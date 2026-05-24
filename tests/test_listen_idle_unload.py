"""Listen daemon idle summarizer unload."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from voxpost.listen import ListenDaemon
from voxpost.summarize import sample_mail_event
from voxpost.summarized_event import SummarizedMailEvent
from voxpost.user_config import VoxpostUserConfig, SpeechConfig, SummarizeConfig, TtsConfig


def _daemon(idle_minutes: int = 10) -> ListenDaemon:
    settings = MagicMock()
    settings.config_dir = MagicMock()
    cfg = VoxpostUserConfig(
        tts=TtsConfig(),
        speech=SpeechConfig(),
        summarize=SummarizeConfig(idle_unload_minutes=idle_minutes),
        config_path=None,
    )
    with patch("voxpost.user_config.load_user_config", return_value=cfg):
        return ListenDaemon(settings, summarize=True)


def test_maybe_unload_summarizer_after_idle():
    daemon = _daemon(idle_minutes=5)
    mock_summarizer = MagicMock()
    daemon._summarizer = mock_summarizer
    daemon._last_summarize_at = time.monotonic() - 400

    daemon._maybe_unload_summarizer()

    mock_summarizer.unload.assert_called_once()
    assert daemon._summarizer is None


def test_maybe_unload_skips_when_recently_used():
    daemon = _daemon(idle_minutes=10)
    mock_summarizer = MagicMock()
    daemon._summarizer = mock_summarizer
    daemon._last_summarize_at = time.monotonic()

    daemon._maybe_unload_summarizer()

    mock_summarizer.unload.assert_not_called()
    assert daemon._summarizer is mock_summarizer


def test_emit_event_updates_last_summarize_timestamp():
    daemon = _daemon()
    event = sample_mail_event()
    summarized = SummarizedMailEvent.from_mail_event(event, "Line.")
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_event.return_value = summarized
    daemon._summarizer = mock_summarizer

    with patch("builtins.print"):
        daemon._emit_event(event)

    assert daemon._last_summarize_at > 0
