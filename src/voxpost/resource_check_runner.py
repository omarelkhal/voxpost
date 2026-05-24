"""Run speech-check emails under resource monitoring (RAM / CPU per case)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from voxpost.resource_monitor import ResourceUsage, current_snapshot, measure_operation
from voxpost.speech_check_cases import SpeechCheckCase, speech_check_cases
from voxpost.speech_check_runner import review_case
from voxpost.summarize import EmailSummarizer, build_model_input


class ResourceScenario(str, Enum):
    """How the summarizer is held across cases."""

    BASELINE = "baseline"
    WARM = "warm"
    COLD = "cold"


@dataclass(frozen=True)
class CaseResourceResult:
    scenario: ResourceScenario
    case: SpeechCheckCase
    usage: ResourceUsage
    summary_preview: str


@dataclass(frozen=True)
class ResourceCheckReport:
    model_id: str
    scenario: ResourceScenario
    process_baseline_mb: float
    model_load: ResourceUsage | None
    cases: tuple[CaseResourceResult, ...]

    @property
    def peak_rss_mb(self) -> float:
        peaks = [c.usage.peak_rss_mb for c in self.cases]
        if self.model_load is not None:
            peaks.append(self.model_load.peak_rss_mb)
        return max(peaks) if peaks else self.process_baseline_mb


def _filter_cases(case_ids: tuple[str, ...] | None) -> tuple[SpeechCheckCase, ...]:
    all_cases = speech_check_cases()
    if not case_ids:
        return all_cases
    by_id = {c.case_id: c for c in all_cases}
    missing = [cid for cid in case_ids if cid not in by_id]
    if missing:
        known = ", ".join(by_id)
        raise ValueError(f"Unknown case id(s): {', '.join(missing)}. Known: {known}")
    return tuple(by_id[cid] for cid in case_ids)


def run_resource_check(
    *,
    config_dir: Path | None = None,
    local_files_only: bool = False,
    model: str | None = None,
    scenario: ResourceScenario = ResourceScenario.WARM,
    case_ids: tuple[str, ...] | None = None,
) -> ResourceCheckReport:
    cases = _filter_cases(case_ids)
    summarizer = EmailSummarizer(
        model=model,
        config_dir=config_dir,
        local_files_only=local_files_only,
    )
    model_id = summarizer.model_id
    baseline = current_snapshot().rss_mb
    model_load: ResourceUsage | None = None
    results: list[CaseResourceResult] = []

    if scenario == ResourceScenario.BASELINE:
        for case in cases:
            def _baseline(case: SpeechCheckCase = case) -> str:
                return build_model_input(case.event)

            _, usage = measure_operation(case.case_id, _baseline)
            results.append(
                CaseResourceResult(
                    scenario=scenario,
                    case=case,
                    usage=usage,
                    summary_preview="(no model — input build only)",
                )
            )
        return ResourceCheckReport(
            model_id=model_id,
            scenario=scenario,
            process_baseline_mb=baseline,
            model_load=None,
            cases=tuple(results),
        )

    if scenario == ResourceScenario.WARM:
        _, model_load = measure_operation("model_load", summarizer._ensure_loaded)
        for case in cases:
            review, usage = measure_operation(
                case.case_id,
                lambda c=case: review_case(summarizer, c),
            )
            preview = review.model_raw[:80] + ("…" if len(review.model_raw) > 80 else "")
            results.append(
                CaseResourceResult(
                    scenario=scenario,
                    case=case,
                    usage=usage,
                    summary_preview=preview,
                )
            )
        return ResourceCheckReport(
            model_id=model_id,
            scenario=scenario,
            process_baseline_mb=baseline,
            model_load=model_load,
            cases=tuple(results),
        )

    # COLD — new summarizer per email (worst case; not how listen works today).
    for case in cases:
        def _cold_email(case: SpeechCheckCase = case) -> str:
            cold = EmailSummarizer(
                model=model,
                config_dir=config_dir,
                local_files_only=local_files_only,
            )
            cold._ensure_loaded()
            return review_case(cold, case).model_raw

        preview_raw, usage = measure_operation(case.case_id, _cold_email)
        preview = preview_raw[:80] + ("…" if len(preview_raw) > 80 else "")
        results.append(
            CaseResourceResult(
                scenario=scenario,
                case=case,
                usage=usage,
                summary_preview=preview,
            )
        )
    return ResourceCheckReport(
        model_id=model_id,
        scenario=scenario,
        process_baseline_mb=baseline,
        model_load=None,
        cases=tuple(results),
    )


def _cpu_count() -> int:
    try:
        import psutil

        return psutil.cpu_count(logical=True) or 1
    except ImportError:
        return 1


def _format_cpu_line(cpu_avg: float) -> str:
    cores = _cpu_count()
    normalized = min(cpu_avg / cores, 100.0) if cores else cpu_avg
    return f"cpu_avg={cpu_avg:.0f}% (~{normalized:.0f}% of {cores} cores)"


def format_resource_report(report: ResourceCheckReport) -> str:
    lines: list[str] = []
    lines.append(f"Voxpost resource check — {report.model_id}")
    lines.append(f"Scenario: {report.scenario.value} (process RSS at start: {report.process_baseline_mb:.0f} MB)")
    lines.append("=" * 72)
    if report.scenario == ResourceScenario.BASELINE:
        lines.append("Baseline only builds model input — no weights loaded.")
    elif report.scenario == ResourceScenario.WARM:
        lines.append("Warm matches `voxpost listen --summarize`: load once, then each email.")
    else:
        lines.append("Cold reloads the full model per email (stress test — not current listen behavior).")
    lines.append("")

    if report.model_load is not None:
        u = report.model_load
        lines.append("--- One-time model load ---")
        lines.append(
            f"  wall={u.wall_seconds:.1f}s  rss {u.rss_before_mb:.0f}→{u.rss_after_mb:.0f} MB "
            f"(+{u.rss_delta_mb:.0f})  peak={u.peak_rss_mb:.0f} MB  {_format_cpu_line(u.cpu_percent_avg)}"
        )
        lines.append("")

    total_wall = sum(c.usage.wall_seconds for c in report.cases)
    lines.append(f"Per-email samples ({len(report.cases)} cases, total infer wall={total_wall:.1f}s):")
    lines.append(
        f"{'case_id':<22} {'wall_s':>7} {'rss_ΔMB':>8} {'peak_MB':>8} {'cpu_%':>6}  label"
    )
    lines.append(f"(cpu_% is process CPU; can exceed 100 on multi-core — see model load line for ~core %)")
    lines.append("-" * 72)
    for row in report.cases:
        u = row.usage
        lines.append(
            f"{row.case.case_id:<22} {u.wall_seconds:7.1f} {u.rss_delta_mb:+8.0f} "
            f"{u.peak_rss_mb:8.0f} {u.cpu_percent_avg:6.0f}  {row.case.label}"
        )
    lines.append("-" * 72)
    lines.append(
        f"Peak RSS during run: {report.peak_rss_mb:.0f} MB  "
        f"(idle after load ≈ {report.cases[-1].usage.rss_after_mb:.0f} MB "
        f"when scenario=warm)"
        if report.cases
        else f"Peak RSS: {report.peak_rss_mb:.0f} MB"
    )
    lines.append("")
    lines.append("Summary previews (first case / last case):")
    if report.cases:
        first = report.cases[0]
        last = report.cases[-1]
        lines.append(f"  [{first.case.case_id}] {first.summary_preview!r}")
        if last is not first:
            lines.append(f"  [{last.case.case_id}] {last.summary_preview!r}")
    return "\n".join(lines).rstrip() + "\n"
