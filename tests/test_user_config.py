"""Tests for voxpost.toml user settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from voxpost.tts import (
    DEFAULT_LANG,
    DEFAULT_SPEED,
    DEFAULT_TOTAL_STEPS,
    DEFAULT_VOICE_NAME,
    supertonic_speaker_from_config,
)
from voxpost.user_config import CONFIG_FILENAME, VoxpostUserConfig, SpeechConfig, SummarizeConfig, TtsConfig, load_user_config, resolved_speakable_lang


def test_load_user_config_defaults_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VOXPOST_SUMMARIZER_CPU_THREADS", raising=False)
    monkeypatch.delenv("VOXPOST_SUMMARIZER_MAX_NEW_TOKENS", raising=False)
    monkeypatch.delenv("VOXPOST_SUMMARIZER_DEVICE", raising=False)
    monkeypatch.delenv("VOXPOST_TTS_DEVICE", raising=False)
    monkeypatch.delenv("VOXPOST_TTS_MODEL", raising=False)
    cfg = load_user_config(tmp_path)
    assert cfg.config_path is None
    from voxpost.tts import DEFAULT_TTS_MODEL

    assert cfg.tts.model == DEFAULT_TTS_MODEL
    assert cfg.tts.device == "auto"
    assert cfg.tts.voice == DEFAULT_VOICE_NAME
    assert cfg.tts.lang == DEFAULT_LANG
    assert cfg.tts.total_steps == DEFAULT_TOTAL_STEPS
    assert cfg.tts.speed == DEFAULT_SPEED
    assert cfg.tts.playback == "auto"
    assert cfg.tts.playback_backend is None
    assert cfg.speech.mode == "fixed"
    assert cfg.speech.target_lang == "en"
    from voxpost.summarize import DEFAULT_MODEL_ID

    assert cfg.summarize.model == DEFAULT_MODEL_ID
    assert cfg.summarize.device == "auto"
    assert cfg.summarize.cpu_threads == 0
    assert cfg.summarize.idle_unload_minutes == 10
    assert cfg.summarize.chat_max_new_tokens == 96
    assert cfg.summarize.load_dtype == "auto"


def test_load_user_config_from_toml(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        """
[tts]
voice = "F1"
lang = "fr"
total_steps = 10
speed = 1.2
playback = "aplay"
auto_download = false

[speech]
mode = "fixed"
target_lang = "de"

[summarize]
model = "csebuetnlp/mT5_multilingual_XLSum"
""".strip(),
        encoding="utf-8",
    )
    cfg = load_user_config(tmp_path)
    assert cfg.config_path == tmp_path / CONFIG_FILENAME
    assert cfg.tts.voice == "F1"
    assert cfg.tts.lang == "fr"
    assert cfg.tts.total_steps == 10
    assert cfg.tts.speed == 1.2
    assert cfg.tts.playback == "aplay"
    assert cfg.tts.playback_backend == "aplay"
    assert cfg.tts.auto_download is False
    assert cfg.speech.mode == "fixed"
    assert cfg.speech.target_lang == "de"
    assert cfg.summarize.model == "csebuetnlp/mT5_multilingual_XLSum"


def test_load_user_config_ollama_backend(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        """
[summarize]
backend = "ollama"
model = "qwen3.5:2b"
ollama_host = "http://127.0.0.1:11434"
""".strip(),
        encoding="utf-8",
    )
    cfg = load_user_config(tmp_path)
    assert cfg.summarize.backend == "ollama"
    assert cfg.summarize.model == "qwen3.5:2b"
    assert cfg.summarize.ollama_host == "http://127.0.0.1:11434"


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / CONFIG_FILENAME).write_text(
        '[tts]\nvoice = "F1"\nlang = "fr"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("VOXPOST_TTS_VOICE", "M1")
    monkeypatch.setenv("VOXPOST_TTS_LANG", "en")
    monkeypatch.setenv("VOXPOST_TTS_SPEED", "0.95")
    cfg = load_user_config(tmp_path)
    assert cfg.tts.voice == "M1"
    assert cfg.tts.lang == "en"
    assert cfg.tts.speed == 0.95


def test_invalid_playback_raises(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        '[tts]\nplayback = "pulseaudio"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="playback"):
        load_user_config(tmp_path)


def test_summarize_device_gpu_alias(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        "[summarize]\ndevice = \"gpu\"\n",
        encoding="utf-8",
    )
    cfg = load_user_config(tmp_path)
    assert cfg.summarize.device == "cuda"


def test_tts_device_and_model_from_toml(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        """
[tts]
model = "supertonic-2"
device = "cuda"
voice = "F2"
""".strip(),
        encoding="utf-8",
    )
    cfg = load_user_config(tmp_path)
    assert cfg.tts.model == "supertonic-2"
    assert cfg.tts.device == "cuda"
    assert cfg.tts.voice == "F2"


def test_invalid_device_raises(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        '[summarize]\ndevice = "tpu"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="device"):
        load_user_config(tmp_path)


def test_supertonic_speaker_from_config():
    cfg = VoxpostUserConfig(
        tts=TtsConfig(voice="F1", lang="fr", total_steps=6, speed=1.1, playback="sounddevice"),
        speech=SpeechConfig(),
        summarize=SummarizeConfig(),
        config_path=None,
    )
    speaker = supertonic_speaker_from_config(cfg)
    assert speaker.voice_name == "F1"
    assert speaker.lang == "fr"


def test_supertonic_speaker_passes_model_and_device():
    cfg = VoxpostUserConfig(
        tts=TtsConfig(model="supertonic-2", device="cpu", voice="M1"),
        speech=SpeechConfig(),
        summarize=SummarizeConfig(),
        config_path=None,
    )
    speaker = supertonic_speaker_from_config(cfg)
    assert speaker._model_name == "supertonic-2"
    assert speaker._device == "cpu"


def test_resolved_speakable_lang_fixed_uses_target_lang(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        """
[speech]
mode = "fixed"
target_lang = "en"

[tts]
lang = "fr"
""".strip(),
        encoding="utf-8",
    )
    assert resolved_speakable_lang(tmp_path) == "en"


def test_resolved_speakable_lang_auto_uses_tts_lang(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text(
        """
[speech]
mode = "auto"
target_lang = "en"

[tts]
lang = "fr"
""".strip(),
        encoding="utf-8",
    )
    assert resolved_speakable_lang(tmp_path) == "fr"
