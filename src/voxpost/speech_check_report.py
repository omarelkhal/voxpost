"""Incremental PR-ready markdown reports for speech-check leaderboard runs."""

from __future__ import annotations

import platform
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from voxpost.email_clean import clean_email_body
from voxpost.speech_check_runner import ModelReviewResult

DEFAULT_REPORT_DIR = Path("docs/benchmarks/runs")


def slugify_model(model_id: str) -> str:
    """Filesystem-safe model slug for report filenames."""
    slug = model_id.strip().replace("/", "-").replace(":", "-").replace(" ", "_")
    return slug.lower()


def new_run_id(*, started_at: datetime | None = None) -> str:
    """Unique id per benchmark run so repeated tests never clobber prior logs."""
    started = started_at or datetime.now(timezone.utc)
    return f"{started.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"


def benchmark_report_filename(
    *,
    model_id: str,
    backend: str,
    total: int,
    run_id: str,
    completed: int,
    status: str,
    input_lang: str = "multi",
    output_lang: str = "en",
) -> str:
    """
    Leaderboard run log name: model, backend, languages, progress, status, run id.

    Example: ``qwen3.5-2b__ollama__in-multi__out-en__24of24__complete__run-….md``
    """
    slug = slugify_model(model_id)
    status_token = status.replace(" ", "-").lower()
    in_token = input_lang.replace(" ", "-").lower()
    out_token = output_lang.replace(" ", "-").lower()
    return (
        f"{slug}__{backend}__in-{in_token}__out-{out_token}__"
        f"{completed}of{total}__{status_token}__run-{run_id}.md"
    )


def allocate_benchmark_report_path(
    *,
    model_id: str,
    backend: str,
    total: int,
    run_id: str,
    input_lang: str = "multi",
    output_lang: str = "en",
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> Path:
    """Pick a new report path; never reuse an existing file from another run."""
    report_dir.mkdir(parents=True, exist_ok=True)
    name = benchmark_report_filename(
        model_id=model_id,
        backend=backend,
        total=total,
        run_id=run_id,
        completed=0,
        status="in progress",
        input_lang=input_lang,
        output_lang=output_lang,
    )
    candidate = report_dir / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        alt = report_dir / f"{stem}-{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1


def _body_preview(body: str, *, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", clean_email_body(body or "")).strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _escape_md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


class IncrementalBenchmarkReport:
    """Update one markdown report in place for the duration of a run."""

    def __init__(
        self,
        *,
        path: Path,
        model_id: str,
        backend: str,
        total: int,
        run_id: str,
        input_lang: str = "multi",
        output_lang: str = "en",
    ) -> None:
        self.path = path
        self.model_id = model_id
        self.backend = backend
        self.total = total
        self.run_id = run_id
        self.input_lang = input_lang
        self.output_lang = output_lang
        self.results: list[ModelReviewResult] = []
        self.started_at = datetime.now(timezone.utc)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write(status="in progress", completed=0)

    @property
    def report_filename(self) -> str:
        return self.path.name

    def append(self, result: ModelReviewResult) -> None:
        self.results.append(result)
        self._write(status="in progress", completed=len(self.results))

    def finalize(self, *, interrupted: bool = False, rename: bool = True) -> None:
        completed = len(self.results)
        if interrupted and completed < self.total:
            self._write(status="stopped early", completed=completed, rename=rename)
            return
        self._write(status="complete", completed=completed, rename=rename)

    def _write(self, *, status: str, completed: int, rename: bool = False) -> None:
        target = self.path
        if rename:
            final_name = benchmark_report_filename(
                model_id=self.model_id,
                backend=self.backend,
                total=self.total,
                run_id=self.run_id,
                completed=completed,
                status=status,
                input_lang=self.input_lang,
                output_lang=self.output_lang,
            )
            target = self.path.parent / final_name
            if target.exists() and target != self.path:
                stem, suffix = target.stem, target.suffix
                index = 2
                while target.exists() and target != self.path:
                    target = self.path.parent / f"{stem}-{index}{suffix}"
                    index += 1

        content = render_benchmark_markdown(
            model_id=self.model_id,
            backend=self.backend,
            results=self.results,
            total=self.total,
            started_at=self.started_at,
            status=status,
            completed=completed,
            run_id=self.run_id,
            report_filename=target.name,
            input_lang=self.input_lang,
            output_lang=self.output_lang,
        )
        target.write_text(content, encoding="utf-8")
        if rename and target != self.path and self.path.exists():
            self.path.unlink()
            self.path = target


def render_benchmark_markdown(
    *,
    model_id: str,
    backend: str,
    results: list[ModelReviewResult],
    total: int,
    started_at: datetime,
    status: str,
    completed: int,
    run_id: str,
    report_filename: str | None = None,
    judge_model: str | None = None,
    input_lang: str = "multi",
    output_lang: str = "en",
) -> str:
    """Build leaderboard PR markdown from sequential manual-review results."""
    fname = report_filename or benchmark_report_filename(
        model_id=model_id,
        backend=backend,
        total=total,
        run_id=run_id,
        completed=completed,
        status=status,
        input_lang=input_lang,
        output_lang=output_lang,
    )
    lines: list[str] = [
        f"# Speech-check benchmark — `{model_id}`",
        "",
        "Incremental run log for the [community leaderboard](../../MODEL_LEADERBOARD.md). "
        "This file updates **after each case**; commit partial progress or stop with Ctrl+C. "
        "**Grade this file** with [MODEL_REVIEW_PROMPT.md](../../contributing/MODEL_REVIEW_PROMPT.md) "
        "(paste the full markdown into your judge chat — not raw terminal output).",
        "",
        "## Run metadata",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Report file | `{fname}` |",
        f"| Run id | `{run_id}` |",
        f"| Model | `{model_id}` |",
        f"| Backend | {backend} |",
        f"| Input language | `{input_lang}` (email/fixture language filter) |",
        f"| Output language | `{output_lang}` (speakable line / TTS language) |",
        f"| Fixture suite | {total} cases |",
        f"| Cases completed | {completed} |",
        f"| Host | {platform.system()} {platform.machine()}, {platform.processor() or 'unknown CPU'} |",
        f"| Started (UTC) | {started_at.strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| Status | **{status}** ({completed}/{total}) |",
        f"| Judge model | {judge_model or '*(pending — e.g. Composer 2.5, Claude, GPT)*'} |",
        "",
        "## Progress",
        "",
        "| # | case_id | label | speakable line | judge grade |",
        "|---|---------|-------|----------------|-------------|",
    ]

    for index, result in enumerate(results, start=1):
        case = result.case
        line = _escape_md_cell(result.model_raw)
        lines.append(
            f"| {index} | `{case.case_id}` | {_escape_md_cell(case.label)} | {line} | *(pending)* |"
        )

    for index in range(len(results) + 1, total + 1):
        lines.append(f"| {index} | — | — | — | — |")

    lines.extend(["", "## Cases", ""])

    for index, result in enumerate(results, start=1):
        case = result.case
        body = _body_preview(case.event.body or "")
        lines.extend(
            [
                f"### {index}/{total} `{case.case_id}`",
                "",
                f"- **Label:** {case.label}",
                f"- **Intent:** {case.intent}",
                f"- **Input lang:** `{case.input_lang}`",
                f"- **From:** {case.event.from_address}",
                f"- **Subject:** {case.event.subject or '*(empty)*'}",
                "",
                "**Body preview**",
                "",
                "```",
                body,
                "```",
                "",
                "**Model speakable line**",
                "",
                f"> {result.model_raw}",
                "",
                "**Judge grade:** *(pending)*",
                "",
            ]
        )

    lines.extend(
        [
            "## Next steps",
            "",
            "1. Paste **this entire markdown file** into a chat with [MODEL_REVIEW_PROMPT.md](../../contributing/MODEL_REVIEW_PROMPT.md).",
            "2. Record the **judge model** name in metadata above (e.g. Composer 2.5).",
            "3. Fill **judge grade** in the progress table and per-case sections (PASS / WEAK / FAIL).",
            "4. Open a PR: leaderboard row in `docs/MODEL_LEADERBOARD.md` + commit this run log.",
            "",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"
