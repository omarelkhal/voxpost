"""Tests for incremental speech-check benchmark reports."""

from datetime import datetime, timezone
from pathlib import Path

from voxpost.events import NewMailEvent
from voxpost.speech_check.case import SpeechCheckCase
from voxpost.speech_check_report import (
    IncrementalBenchmarkReport,
    allocate_benchmark_report_path,
    benchmark_report_filename,
    render_benchmark_markdown,
    slugify_model,
)
from voxpost.speech_check_runner import ModelReviewResult


def _sample_result(case_id: str = "en_short_ack") -> ModelReviewResult:
    case = SpeechCheckCase(
        case_id=case_id,
        label="English — short acknowledgment",
        intent="Quick thanks and confirm 3pm meeting.",
        event=NewMailEvent(
            account_id="eval@test.local",
            message_id="m1",
            thread_id="t1",
            history_id="1",
            from_address="Jordan Lee <jordan@team.io>",
            subject="Re: sync",
            body="Thanks — 3pm tomorrow works for me.",
        ),
    )
    return ModelReviewResult(case=case, model_raw="Jordan Lee confirms three p.m. tomorrow works.")


def test_slugify_model():
    assert slugify_model("Qwen/Qwen3.5-0.8B") == "qwen-qwen3.5-0.8b"
    assert slugify_model("qwen3.5:2b") == "qwen3.5-2b"


def test_benchmark_report_filename_includes_run_id():
    name = benchmark_report_filename(
        model_id="qwen3.5:2b",
        backend="ollama",
        completed=24,
        total=24,
        status="complete",
        run_id="20260524-143052-a1b2c3",
    )
    assert name == "qwen3.5-2b__ollama__24of24__complete__run-20260524-143052-a1b2c3.md"


def test_allocate_benchmark_report_path_skips_existing(tmp_path: Path):
    run_id = "20260524-120000-dead01"
    first = allocate_benchmark_report_path(
        model_id="qwen3.5:2b",
        backend="ollama",
        total=24,
        run_id=run_id,
        report_dir=tmp_path,
    )
    first.write_text("prior run", encoding="utf-8")
    second = allocate_benchmark_report_path(
        model_id="qwen3.5:2b",
        backend="ollama",
        total=24,
        run_id=run_id,
        report_dir=tmp_path,
    )
    assert second != first
    assert second.name.endswith("-2.md")
    assert first.read_text(encoding="utf-8") == "prior run"


def test_incremental_report_updates_in_place(tmp_path: Path):
    run_id = "20260524-120000-abc123"
    path = allocate_benchmark_report_path(
        model_id="qwen3.5:2b",
        backend="ollama",
        total=2,
        run_id=run_id,
        report_dir=tmp_path,
    )
    writer = IncrementalBenchmarkReport(
        path=path,
        model_id="qwen3.5:2b",
        backend="ollama",
        total=2,
        run_id=run_id,
    )
    writer.append(_sample_result())
    assert writer.path.exists()
    assert "(1/2)" in writer.path.read_text(encoding="utf-8")
    writer.finalize(rename=False)
    assert writer.path.exists()
    assert "complete" in writer.path.read_text(encoding="utf-8").lower()


def test_render_benchmark_markdown_in_progress():
    run_id = "20260524-120000-abc123"
    fname = benchmark_report_filename(
        model_id="qwen3.5:2b",
        backend="ollama",
        total=24,
        run_id=run_id,
        completed=1,
        status="in progress",
    )
    md = render_benchmark_markdown(
        model_id="qwen3.5:2b",
        backend="ollama",
        results=[_sample_result()],
        total=24,
        started_at=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
        status="in progress",
        completed=1,
        run_id=run_id,
        report_filename=fname,
    )
    assert fname in md
    assert run_id in md
    assert "qwen3.5:2b" in md
    assert "in progress" in md
    assert "(1/24)" in md
    assert "`en_short_ack`" in md
    assert "*(pending)*" in md
    assert "entire markdown" in md.lower()
