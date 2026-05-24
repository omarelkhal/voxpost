"""Run sample emails through the summarizer for speakable-line review."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from voxpost.email_clean import clean_email_body
from voxpost.speakable_fallback import fallback_speakable_line, is_usable_summary
from voxpost.speakable_polish import polish_for_tts
from voxpost.speech_check_cases import SpeechCheckCase, speech_check_cases
from voxpost.speech_check_parallel import (
    WorkerJob,
    apply_worker_cpu_threads,
    config_dir_from_job,
    resolve_workers,
    run_in_process_pool,
)
from voxpost.summarize import EmailSummarizer, _normalize_body, _uses_causal_chat, build_model_input


def _build_worker_job(
    *,
    config_dir: Path | None,
    local_files_only: bool,
    model: str | None,
    workers: int,
    case_count: int,
) -> tuple[WorkerJob, int]:
    effective = resolve_workers(workers, case_count=case_count)
    job = WorkerJob(
        config_dir=str(config_dir) if config_dir else None,
        local_files_only=local_files_only,
        model=model,
        effective_workers=effective,
    )
    return job, effective


def filter_speech_cases(case_ids: tuple[str, ...] | None) -> tuple[SpeechCheckCase, ...]:
    """Subset fixtures by id; default is all speech-check cases."""
    all_cases = speech_check_cases()
    if not case_ids:
        return all_cases
    by_id = {c.case_id: c for c in all_cases}
    missing = [cid for cid in case_ids if cid not in by_id]
    if missing:
        known = ", ".join(sorted(by_id))
        raise ValueError(f"Unknown case id(s): {', '.join(missing)}. Known: {known}")
    return tuple(by_id[cid] for cid in case_ids)


def _parse_case_ids(raw: str | None) -> tuple[str, ...] | None:
    if not raw or not raw.strip():
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def workers_cli_help() -> str:
    from voxpost.speech_check_parallel import estimated_worker_ram_mb

    return (
        "Parallel process workers (default 1). Each worker loads the model "
        f"(~{estimated_worker_ram_mb(1)} MB RAM on CPU). Use 2–4 on multi-core "
        "machines with enough memory."
    )


class SpeechGrade(str, Enum):
    PASS = "PASS"
    WEAK = "WEAK"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ModelReviewResult:
    """Raw model output for human pass/fail review (no auto grading)."""

    case: SpeechCheckCase
    model_raw: str


@dataclass(frozen=True)
class SpeechCheckResult:
    case: SpeechCheckCase
    model_raw: str
    speakable_line: str
    used_fallback: bool
    grade: SpeechGrade
    notes: tuple[str, ...]


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(n.lower() in lower for n in needles)


def _contains_bad(text: str, needles: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return [n for n in needles if n.lower() in lower]


def grade_speech_line(
    case: SpeechCheckCase,
    speakable_line: str,
    *,
    used_fallback: bool,
) -> tuple[SpeechGrade, tuple[str, ...]]:
    notes: list[str] = []
    bad = _contains_bad(speakable_line, case.must_not_mention)
    if bad:
        notes.append(f"forbidden phrases: {', '.join(bad)}")
        return SpeechGrade.FAIL, tuple(notes)

    words = speakable_line.split()
    if len(words) > case.max_words:
        notes.append(f"too long ({len(words)} words, max {case.max_words})")

    if case.must_mention_any and not _contains_any(speakable_line, case.must_mention_any):
        notes.append(f"missing intent keywords (any of: {', '.join(case.must_mention_any)})")
        if used_fallback:
            return SpeechGrade.WEAK, tuple(notes)
        return SpeechGrade.FAIL, tuple(notes)

    if notes:
        return SpeechGrade.WEAK, tuple(notes)
    if used_fallback:
        notes.append("fallback template (model output rejected)")
        return SpeechGrade.WEAK, tuple(notes)
    return SpeechGrade.PASS, tuple(notes)


def review_case(summarizer: EmailSummarizer, case: SpeechCheckCase) -> ModelReviewResult:
    """Run one case and return raw model text only — human decides pass/fail."""
    model_raw = summarizer.summarize_event_text(case.event)
    polished = polish_for_tts(model_raw)
    return ModelReviewResult(case=case, model_raw=polished)


def run_model_review(
    *,
    config_dir: Path | None = None,
    local_files_only: bool = False,
    model: str | None = None,
    case_ids: tuple[str, ...] | None = None,
    workers: int = 1,
) -> list[ModelReviewResult]:
    cases = filter_speech_cases(case_ids)
    job, effective = _build_worker_job(
        config_dir=config_dir,
        local_files_only=local_files_only,
        model=model,
        workers=workers,
        case_count=len(cases),
    )
    return run_in_process_pool(cases, effective, _worker_model_review, job)


def _worker_model_review(
    chunk: list[SpeechCheckCase],
    job: WorkerJob,
) -> list[ModelReviewResult]:
    apply_worker_cpu_threads(job)
    summarizer = EmailSummarizer(
        model=job.model,
        config_dir=config_dir_from_job(job),
        local_files_only=job.local_files_only,
    )
    return [review_case(summarizer, case) for case in chunk]


def format_manual_review_report(
    results: list[ModelReviewResult],
    *,
    model_id: str | None = None,
) -> str:
    """Print model outputs for human review — no automated pass/fail."""
    lines: list[str] = []
    label = model_id or "summarizer"
    lines.append(f"Voxpost speech check (manual review) — {label}")
    lines.append("=" * 60)
    lines.append(
        "Read each summary aloud in your head. Mark PASS if you would "
        "happily hear it for this email; FAIL otherwise."
    )
    lines.append("")

    for i, r in enumerate(results, start=1):
        c = r.case
        body = clean_email_body(c.event.body or "")
        body = re.sub(r"\s+", " ", body).strip()

        lines.append(f"--- Case {i}/{len(results)}: {c.case_id} ---")
        lines.append(f"Label:  {c.label}")
        lines.append(f"Intent: {c.intent}")
        lines.append(f"From:   {c.event.from_address}")
        lines.append(f"Subj:   {c.event.subject}")
        lines.append(f"Body:")
        lines.append(f"  {body}")
        lines.append(f"Model summary:")
        lines.append(f"  {r.model_raw}")
        lines.append(f"Your call: PASS / FAIL")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


@dataclass(frozen=True)
class FormatComparisonRow:
    case: SpeechCheckCase
    plain_raw: str
    plain_grade: SpeechGrade
    plain_spoken: str
    plain_fallback: bool
    structured_raw: str
    structured_grade: SpeechGrade
    structured_spoken: str
    structured_fallback: bool


def _check_case_with_format(
    summarizer: EmailSummarizer,
    case: SpeechCheckCase,
    *,
    input_format: str,
) -> tuple[str, str, SpeechGrade, bool]:
    source_body = _normalize_body(case.event)
    model_raw = summarizer.summarize_event_text(case.event, input_format=input_format)
    polished = polish_for_tts(model_raw)
    passed = is_usable_summary(
        polished,
        source=source_body,
        event=case.event,
        chat_lm=_uses_causal_chat(summarizer.model_id),
    )
    if passed:
        speakable = polished
        used_fallback = False
    else:
        speakable = polish_for_tts(fallback_speakable_line(case.event))
        used_fallback = True
    grade, _ = grade_speech_line(case, speakable, used_fallback=used_fallback)
    return model_raw, speakable, grade, used_fallback


def run_format_comparison(
    *,
    config_dir: Path | None = None,
    local_files_only: bool = False,
    model: str | None = None,
    case_ids: tuple[str, ...] | None = None,
    workers: int = 1,
) -> list[FormatComparisonRow]:
    """A/B plain vs structured JSON input on the same loaded chat model."""
    cases = filter_speech_cases(case_ids)
    job, effective = _build_worker_job(
        config_dir=config_dir,
        local_files_only=local_files_only,
        model=model,
        workers=workers,
        case_count=len(cases),
    )
    return run_in_process_pool(cases, effective, _worker_format_comparison, job)


def _worker_format_comparison(
    chunk: list[SpeechCheckCase],
    job: WorkerJob,
) -> list[FormatComparisonRow]:
    apply_worker_cpu_threads(job)
    summarizer = EmailSummarizer(
        model=job.model,
        config_dir=config_dir_from_job(job),
        local_files_only=job.local_files_only,
    )
    rows: list[FormatComparisonRow] = []
    for case in chunk:
        plain_raw, plain_spoken, plain_grade, plain_fb = _check_case_with_format(
            summarizer, case, input_format="plain"
        )
        struct_raw, struct_spoken, struct_grade, struct_fb = _check_case_with_format(
            summarizer, case, input_format="structured"
        )
        rows.append(
            FormatComparisonRow(
                case=case,
                plain_raw=plain_raw,
                plain_grade=plain_grade,
                plain_spoken=plain_spoken,
                plain_fallback=plain_fb,
                structured_raw=struct_raw,
                structured_grade=struct_grade,
                structured_spoken=struct_spoken,
                structured_fallback=struct_fb,
            )
        )
    return rows


def format_comparison_report(
    rows: list[FormatComparisonRow],
    *,
    model_id: str | None = None,
) -> str:
    def _count(fmt: str, grade: SpeechGrade) -> int:
        if fmt == "plain":
            return sum(1 for r in rows if r.plain_grade == grade)
        return sum(1 for r in rows if r.structured_grade == grade)

    label = model_id or "summarizer"
    lines: list[str] = [
        f"Voxpost input format comparison — {label}",
        "=" * 60,
        (
            f"Plain:      {_count('plain', SpeechGrade.PASS)} pass, "
            f"{_count('plain', SpeechGrade.WEAK)} weak, "
            f"{_count('plain', SpeechGrade.FAIL)} fail"
        ),
        (
            f"Structured: {_count('structured', SpeechGrade.PASS)} pass, "
            f"{_count('structured', SpeechGrade.WEAK)} weak, "
            f"{_count('structured', SpeechGrade.FAIL)} fail"
        ),
        "",
    ]
    for r in rows:
        c = r.case
        winner = "tie"
        rank = {SpeechGrade.PASS: 3, SpeechGrade.WEAK: 2, SpeechGrade.FAIL: 1}
        if rank[r.structured_grade] > rank[r.plain_grade]:
            winner = "structured"
        elif rank[r.plain_grade] > rank[r.structured_grade]:
            winner = "plain"
        lines.append(f"--- {c.case_id} — {c.label} (better: {winner}) ---")
        lines.append(f"  Plain model:      {r.plain_raw!r}")
        lines.append(f"  Plain spoken:     {r.plain_spoken!r} [{r.plain_grade.value}]")
        lines.append(f"  Structured model: {r.structured_raw!r}")
        lines.append(
            f"  Structured spoken:{r.structured_spoken!r} [{r.structured_grade.value}]"
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check_case(summarizer: EmailSummarizer, case: SpeechCheckCase) -> SpeechCheckResult:
    source_body = _normalize_body(case.event)
    model_raw = summarizer.summarize_event_text(case.event)
    polished = polish_for_tts(model_raw)
    passed = is_usable_summary(
        polished,
        source=source_body,
        event=case.event,
        chat_lm=_uses_causal_chat(summarizer.model_id),
    )
    if passed:
        speakable = polished
        used_fallback = False
    else:
        speakable = polish_for_tts(fallback_speakable_line(case.event))
        used_fallback = True

    grade, notes = grade_speech_line(case, speakable, used_fallback=used_fallback)
    return SpeechCheckResult(
        case=case,
        model_raw=model_raw,
        speakable_line=speakable,
        used_fallback=used_fallback,
        grade=grade,
        notes=notes,
    )


def run_speech_check(
    *,
    config_dir: Path | None = None,
    local_files_only: bool = False,
    model: str | None = None,
    case_ids: tuple[str, ...] | None = None,
    workers: int = 1,
) -> list[SpeechCheckResult]:
    cases = filter_speech_cases(case_ids)
    job, effective = _build_worker_job(
        config_dir=config_dir,
        local_files_only=local_files_only,
        model=model,
        workers=workers,
        case_count=len(cases),
    )
    return run_in_process_pool(cases, effective, _worker_speech_check, job)


def _worker_speech_check(
    chunk: list[SpeechCheckCase],
    job: WorkerJob,
) -> list[SpeechCheckResult]:
    apply_worker_cpu_threads(job)
    summarizer = EmailSummarizer(
        model=job.model,
        config_dir=config_dir_from_job(job),
        local_files_only=job.local_files_only,
    )
    return [check_case(summarizer, case) for case in chunk]


def format_check_report(
    results: list[SpeechCheckResult],
    *,
    model_id: str | None = None,
) -> str:
    lines: list[str] = []
    counts = {g: 0 for g in SpeechGrade}
    for r in results:
        counts[r.grade] += 1

    label = model_id or "summarizer"
    lines.append(f"Voxpost speech check — {label}")
    lines.append("=" * 60)
    lines.append(
        f"Summary: {counts[SpeechGrade.PASS]} pass, "
        f"{counts[SpeechGrade.WEAK]} weak, {counts[SpeechGrade.FAIL]} fail "
        f"(of {len(results)} cases)"
    )
    lines.append("")

    for r in results:
        c = r.case
        body_preview = clean_email_body(c.event.body or "")
        body_preview = re.sub(r"\s+", " ", body_preview).strip()
        if len(body_preview) > 100:
            body_preview = body_preview[:100] + "…"

        lines.append(f"[{r.grade.value}] {c.case_id} — {c.label}")
        lines.append(f"  Intent: {c.intent}")
        lines.append(f"  Body:   {body_preview!r}")
        lines.append(f"  Model:  {r.model_raw!r}")
        lines.append(f"  Spoken: {r.speakable_line!r}")
        if r.used_fallback:
            lines.append("  Path:   fallback (quality gate rejected model)")
        else:
            lines.append("  Path:   model output accepted")
        if r.notes:
            lines.append(f"  Notes:  {'; '.join(r.notes)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def check_case_hf_prompt(
    case: SpeechCheckCase,
    *,
    model: str,
    config_dir: Path | None = None,
    input_format: str | None = None,
    provider: str | None = None,
) -> SpeechCheckResult:
    """Grade raw HF inference output — no local fallbacks (prompt oracle)."""
    from voxpost.hf_inference_prompt import summarize_event_hf
    from voxpost.speakable_gate import adjust_misapplied_spam_template
    from voxpost.summarize import _normalize_body

    model_raw = summarize_event_hf(
        case.event,
        model=model,
        config_dir=config_dir,
        input_format=input_format,
        provider=provider,
    )
    model_raw = adjust_misapplied_spam_template(
        model_raw,
        case.event,
        normalized_body=_normalize_body(case.event),
    )
    speakable = polish_for_tts(model_raw)
    grade, notes = grade_speech_line(case, speakable, used_fallback=False)
    return SpeechCheckResult(
        case=case,
        model_raw=model_raw,
        speakable_line=speakable,
        used_fallback=False,
        grade=grade,
        notes=notes,
    )


def run_hf_prompt_check(
    *,
    model: str,
    config_dir: Path | None = None,
    case_ids: tuple[str, ...] | None = None,
    input_format: str | None = None,
    provider: str | None = None,
) -> list[SpeechCheckResult]:
    """Run speech-check fixtures through HF Inference with Voxpost prompts."""
    cases = filter_speech_cases(case_ids)
    return [
        check_case_hf_prompt(
            case,
            model=model,
            config_dir=config_dir,
            input_format=input_format,
            provider=provider,
        )
        for case in cases
    ]


def format_hf_prompt_report(
    results: list[SpeechCheckResult],
    *,
    model_id: str,
    input_format: str,
) -> str:
    header = [
        f"Voxpost HF prompt check — {model_id} ({input_format} input)",
        "=" * 60,
        "Cloud oracle: Voxpost chat prompts, raw model output only (no fallbacks).",
        "",
    ]
    body = format_check_report(results, model_id=model_id)
    body_lines = body.split("\n", 3)
    if len(body_lines) >= 4:
        return "\n".join(header) + body_lines[3]
    return "\n".join(header) + body
