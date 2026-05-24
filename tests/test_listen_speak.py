"""Listen daemon TTS wiring (Block 4)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from voxpost.console import ListenConsole
from voxpost.events import NewMailEvent
from voxpost.listen import ListenDaemon
from voxpost.summarize import sample_mail_event
from voxpost.summarized_event import SummarizedMailEvent
from voxpost.user_config import VoxpostUserConfig, SpeechConfig, SummarizeConfig, TtsConfig


def _listen_daemon(**kwargs):
    settings = MagicMock()
    settings.config_dir = MagicMock()
    cfg = VoxpostUserConfig(
        tts=TtsConfig(),
        speech=SpeechConfig(),
        summarize=SummarizeConfig(),
        config_path=None,
    )
    with patch("voxpost.user_config.load_user_config", return_value=cfg):
        return ListenDaemon(settings, **kwargs)


def _sample_event() -> NewMailEvent:
    return sample_mail_event()


def test_emit_event_speaks_summarized_line():
    speaker = MagicMock()
    event = _sample_event()
    summarized = SummarizedMailEvent.from_mail_event(
        event,
        "Alex says the staging deploy failed.",
    )

    daemon = _listen_daemon(
        summarize=True,
        speak=True,
        speaker=speaker,
    )
    daemon._console = ListenConsole(json_mode=True)
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_event.return_value = summarized
    daemon._summarizer = mock_summarizer

    with patch("builtins.print") as print_mock:
        with patch("voxpost.tts.speak_from_user_config") as speak_mock:
            daemon._emit_event(event)

    print_mock.assert_called_once()
    speak_mock.assert_called_once()
    assert speak_mock.call_args.args[0] == "Alex says the staging deploy failed."


def test_emit_event_tts_failure_does_not_raise():
    speaker = MagicMock()
    speaker.speak.side_effect = RuntimeError("playback failed")
    event = _sample_event()
    summarized = SummarizedMailEvent.from_mail_event(event, "Short line.")

    daemon = _listen_daemon(
        summarize=True,
        speak=True,
        speaker=speaker,
    )
    daemon._console = ListenConsole(json_mode=True)
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_event.return_value = summarized
    daemon._summarizer = mock_summarizer

    with patch("builtins.print"):
        with patch("voxpost.tts.speak_from_user_config", side_effect=RuntimeError("playback failed")):
            daemon._emit_event(event)


def test_run_listen_speak_implies_summarize():
    settings = MagicMock()
    with patch("voxpost.listen.ListenDaemon") as daemon_cls:
        from voxpost.listen import run_listen

        run_listen(settings, speak=True)
        daemon_cls.assert_called_once()
        kwargs = daemon_cls.call_args.kwargs
        assert kwargs["summarize"] is True
        assert kwargs["speak"] is True


def test_process_notification_summarize_does_not_deadlock():
    """Regression: _emit_event acquires lock; must not call it under the same lock."""
    settings = MagicMock()
    settings.fetch_delay_seconds = 0
    cfg = VoxpostUserConfig(
        tts=TtsConfig(),
        speech=SpeechConfig(),
        summarize=SummarizeConfig(),
        config_path=None,
    )
    event = _sample_event()
    summarized = SummarizedMailEvent.from_mail_event(event, "Short summary line.")

    with patch("voxpost.user_config.load_user_config", return_value=cfg):
        daemon = ListenDaemon(settings, summarize=True)
    daemon._console = ListenConsole(json_mode=True)

    daemon._account_email = "user@example.com"
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_event.return_value = summarized
    daemon._summarizer = mock_summarizer
    daemon._service = MagicMock()

    from voxpost.state import WatchState

    with (
        patch(
            "voxpost.listen.list_new_mail_events",
            return_value=([event], "999"),
        ),
        patch.object(daemon._state_store, "load", return_value=WatchState(history_id="1")),
        patch.object(daemon._state_store, "update_history_id") as update_cursor,
        patch("builtins.print") as print_mock,
    ):
        daemon._process_notification("user@example.com", "100")

    mock_summarizer.summarize_event.assert_called_once_with(event)
    print_mock.assert_called_once()
    update_cursor.assert_called_once_with("999")
