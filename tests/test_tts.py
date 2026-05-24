"""Tests for Block 4 Supertonic TTS wrapper."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from voxpost.tts import (
    DEFAULT_CHIME_PAUSE_MS,
    DEFAULT_LANG,
    DEFAULT_SPEED,
    DEFAULT_TOTAL_STEPS,
    DEFAULT_VOICE_NAME,
    SupertonicSpeaker,
    play_audio_blocking,
    play_notification_chime,
    resolve_onnx_providers,
    resolve_playback,
    speak_with_chime,
    synthesize_chime,
)


def test_resolve_onnx_providers_auto_cpu_only():
    fake_ort = MagicMock()
    fake_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    with patch.dict("sys.modules", {"onnxruntime": fake_ort}):
        assert resolve_onnx_providers("auto") == ["CPUExecutionProvider"]


def test_resolve_onnx_providers_auto_cuda_when_available():
    fake_ort = MagicMock()
    fake_ort.get_available_providers.return_value = [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    with patch.dict("sys.modules", {"onnxruntime": fake_ort}):
        assert resolve_onnx_providers("auto") == [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]


def test_resolve_playback_prefers_sounddevice():
    with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
        assert resolve_playback() == "sounddevice"


def test_resolve_playback_falls_back_to_aplay():
    with patch.dict("sys.modules", {"sounddevice": None}):
        with patch("voxpost.tts.shutil.which", return_value="/usr/bin/aplay"):
            assert resolve_playback() == "aplay"


def test_supertonic_speaker_synthesize_uses_defaults():
    mock_engine = MagicMock()
    mock_engine.sample_rate = 44100
    mock_style = MagicMock()
    mock_engine.get_voice_style.return_value = mock_style
    mock_engine.synthesize.return_value = (
        __import__("numpy").array([[0.1, 0.2]], dtype="float32"),
        __import__("numpy").array([0.01]),
    )

    speaker = SupertonicSpeaker()
    fake_supertonic = SimpleNamespace(TTS=MagicMock(return_value=mock_engine))
    with patch("voxpost.tts._configure_supertonic_providers"):
        with patch.dict("sys.modules", {"supertonic": fake_supertonic}):
            audio, sample_rate = speaker.synthesize("Hello from Voxpost.")

    mock_engine.get_voice_style.assert_called_once_with(DEFAULT_VOICE_NAME)
    mock_engine.synthesize.assert_called_once_with(
        "Hello from Voxpost.",
        voice_style=mock_style,
        lang=DEFAULT_LANG,
        total_steps=DEFAULT_TOTAL_STEPS,
        speed=DEFAULT_SPEED,
        verbose=False,
    )
    assert sample_rate == 44100
    assert audio.shape == (2,)


def test_supertonic_speaker_speak_plays_audio():
    speaker = SupertonicSpeaker(playback_backend="sounddevice")
    fake_audio = __import__("numpy").array([0.0, 0.1], dtype="float32")

    with patch.object(speaker, "synthesize", return_value=(fake_audio, 44100)):
        with patch("voxpost.tts.play_audio_blocking") as play_mock:
            speaker.speak("  Test line  ")

    play_mock.assert_called_once_with(fake_audio, 44100, "sounddevice")


def test_supertonic_speaker_rejects_empty_text():
    speaker = SupertonicSpeaker()
    with pytest.raises(ValueError, match="non-empty"):
        speaker.speak("   ")


def test_supertonic_speaker_missing_extra_raises():
    speaker = SupertonicSpeaker()
    with patch.dict("sys.modules", {"supertonic": None}):
        with pytest.raises(RuntimeError, match="voxpost\\[tts\\]"):
            speaker.warmup()


def test_play_audio_blocking_unknown_backend():
    audio = __import__("numpy").array([0.0], dtype="float32")
    with pytest.raises(RuntimeError, match="unknown playback backend"):
        play_audio_blocking(audio, 44100, "invalid")


def test_synthesize_chime_produces_audio():
    audio = synthesize_chime()
    assert audio.size > 0
    assert audio.dtype.name == "float32"


def test_play_notification_chime_no_backend_skips():
    with patch("voxpost.tts.resolve_playback", return_value=None):
        with patch("voxpost.tts.play_audio_blocking") as play_mock:
            play_notification_chime()
    play_mock.assert_not_called()


def test_speak_with_chime_synthesizes_before_chime():
    speaker = SupertonicSpeaker(playback_backend="sounddevice")
    fake_audio = __import__("numpy").array([0.0, 0.1], dtype="float32")
    order: list[str] = []

    def _synthesize(_text: str):
        order.append("synthesize")
        return fake_audio, 44100

    def _chime(**_kwargs):
        order.append("chime")

    def _play(*_args, **_kwargs):
        order.append("play")

    with patch.object(speaker, "synthesize", side_effect=_synthesize):
        with patch("voxpost.tts.play_notification_chime", side_effect=_chime):
            with patch("voxpost.tts.play_audio_blocking", side_effect=_play):
                with patch("voxpost.tts.time.sleep"):
                    speak_with_chime(
                        speaker,
                        "Hello",
                        chime_before_speak=True,
                        chime_pause_ms=DEFAULT_CHIME_PAUSE_MS,
                    )

    assert order == ["synthesize", "chime", "play"]


def test_speak_with_chime_disabled_skips_chime():
    speaker = SupertonicSpeaker(playback_backend="sounddevice")
    fake_audio = __import__("numpy").array([0.0], dtype="float32")
    with patch("voxpost.tts.play_notification_chime") as chime_mock:
        with patch.object(speaker, "synthesize", return_value=(fake_audio, 44100)):
            with patch("voxpost.tts.play_audio_blocking") as play_mock:
                speak_with_chime(speaker, "Hello", chime_before_speak=False)
    chime_mock.assert_not_called()
    play_mock.assert_called_once_with(fake_audio, 44100, "sounddevice")
