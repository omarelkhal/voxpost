"""Resource check runner tests (no model load)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from voxpost.resource_check_runner import ResourceScenario, format_resource_report, run_resource_check
from voxpost.speech_check_runner import ModelReviewResult


@patch("voxpost.resource_check_runner.review_case")
@patch("voxpost.resource_check_runner.EmailSummarizer")
def test_warm_scenario_reports_model_load_and_cases(mock_summarizer_cls, mock_review):
    mock_summarizer = MagicMock()
    mock_summarizer.model_id = "test/model"
    mock_summarizer._ensure_loaded = MagicMock()
    mock_summarizer_cls.return_value = mock_summarizer

    case = MagicMock()
    case.case_id = "en_short_ack"
    case.label = "Short ack"
    mock_review.return_value = ModelReviewResult(case=case, model_raw="Got it.")

    with patch("voxpost.resource_check_runner.speech_check_cases", return_value=(case,)):
        with patch("voxpost.resource_check_runner.measure_operation") as mock_measure:
            from voxpost.resource_monitor import ResourceUsage

            mock_measure.side_effect = [
                (None, ResourceUsage("model_load", 1.0, 100, 400, 300, 400, 50.0)),
                (mock_review.return_value, ResourceUsage("en_short_ack", 0.5, 400, 405, 5, 410, 80.0)),
            ]
            report = run_resource_check(scenario=ResourceScenario.WARM, case_ids=("en_short_ack",))

    assert report.model_load is not None
    assert report.model_load.rss_delta_mb == 300
    assert len(report.cases) == 1
    text = format_resource_report(report)
    assert "test/model" in text
    assert "model load" in text.lower()
    assert "en_short_ack" in text


def test_baseline_scenario_skips_model():
    from voxpost.speech_check_cases import speech_check_cases

    case = next(c for c in speech_check_cases() if c.case_id == "en_minimal_ping")
    report = run_resource_check(
        scenario=ResourceScenario.BASELINE,
        case_ids=("en_minimal_ping",),
    )

    assert report.model_load is None
    assert report.cases[0].summary_preview.startswith("(no model")
    assert report.cases[0].case.case_id == case.case_id
