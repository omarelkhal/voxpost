"""User-facing settings from ~/.config/voxpost/voxpost.toml (optional)."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from voxpost.config import _default_config_dir
from voxpost.summarize import (
    CHAT_LM_MAX_NEW_TOKENS,
    DEFAULT_MODEL_ID,
)
from voxpost.tts import (
    DEFAULT_CHIME_BEFORE_SPEAK,
    DEFAULT_CHIME_PAUSE_MS,
    DEFAULT_LANG,
    DEFAULT_SPEED,
    DEFAULT_TOTAL_STEPS,
    DEFAULT_TTS_MODEL,
    DEFAULT_VOICE_NAME,
)

CONFIG_FILENAME = "voxpost.toml"
_VALID_PLAYBACK = frozenset({"auto", "sounddevice", "aplay"})
_VALID_SPEECH_MODES = frozenset({"auto", "fixed"})
_VALID_DEVICES = frozenset({"auto", "cpu", "cuda", "gpu", "mps"})
_VALID_TTS_MODELS = frozenset({"supertonic", "supertonic-2", "supertonic-3"})


@dataclass(frozen=True)
class TtsConfig:
    model: str = DEFAULT_TTS_MODEL
    device: str = "auto"
    voice: str = DEFAULT_VOICE_NAME
    lang: str = DEFAULT_LANG
    total_steps: int = DEFAULT_TOTAL_STEPS
    speed: float = DEFAULT_SPEED
    playback: str = "auto"
    auto_download: bool = True
    chime_before_speak: bool = DEFAULT_CHIME_BEFORE_SPEAK
    chime_pause_ms: int = DEFAULT_CHIME_PAUSE_MS
    chime_file: str | None = None

    @property
    def playback_backend(self) -> str | None:
        """Return explicit backend or None to resolve at speak time."""
        if self.playback == "auto":
            return None
        return self.playback


@dataclass(frozen=True)
class SpeechConfig:
    mode: str = "fixed"
    target_lang: str = "en"


@dataclass(frozen=True)
class SummarizeConfig:
    model: str = DEFAULT_MODEL_ID
    backend: str = "transformers"
    ollama_host: str = "http://localhost:11434"
    device: str = "auto"
    cpu_threads: int = 0
    idle_unload_minutes: int = 10
    chat_max_new_tokens: int = CHAT_LM_MAX_NEW_TOKENS
    load_dtype: str = "auto"
    chat_input_format: str = "plain"


_VALID_CHAT_INPUT_FORMATS = frozenset({"plain", "structured"})
_VALID_SUMMARIZE_BACKENDS = frozenset({"transformers", "ollama"})


@dataclass(frozen=True)
class VoxpostUserConfig:
    tts: TtsConfig
    speech: SpeechConfig
    summarize: SummarizeConfig
    config_path: Path | None


def _env_str(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _env_bool(name: str) -> bool | None:
    raw = _env_str(name)
    if raw is None:
        return None
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str) -> int | None:
    raw = _env_str(name)
    if raw is None:
        return None
    return int(raw)


def _env_float(name: str) -> float | None:
    raw = _env_str(name)
    if raw is None:
        return None
    return float(raw)


def _normalize_device(raw: str, *, section: str) -> str:
    device = raw.strip().lower()
    if device == "gpu":
        device = "cuda"
    if device not in _VALID_DEVICES:
        raise ValueError(
            f"[{section}].device must be one of {sorted(_VALID_DEVICES)}, got {raw!r}"
        )
    return device


def _parse_tts_table(raw: dict[str, object]) -> TtsConfig:
    model = str(raw.get("model", DEFAULT_TTS_MODEL)).strip()
    if model not in _VALID_TTS_MODELS:
        raise ValueError(
            f"[tts].model must be one of {sorted(_VALID_TTS_MODELS)}, got {model!r}"
        )
    device = _normalize_device(str(raw.get("device", "auto")), section="tts")
    voice = str(raw.get("voice", DEFAULT_VOICE_NAME))
    lang = str(raw.get("lang", DEFAULT_LANG))
    total_steps = int(raw.get("total_steps", DEFAULT_TOTAL_STEPS))
    speed = float(raw.get("speed", DEFAULT_SPEED))
    playback = str(raw.get("playback", "auto")).lower()
    auto_download = bool(raw.get("auto_download", True))
    chime_before_speak = bool(raw.get("chime_before_speak", DEFAULT_CHIME_BEFORE_SPEAK))
    chime_pause_ms = int(raw.get("chime_pause_ms", DEFAULT_CHIME_PAUSE_MS))
    chime_raw = raw.get("chime_file")
    chime_file = str(chime_raw).strip() if chime_raw else None

    if playback not in _VALID_PLAYBACK:
        raise ValueError(
            f"[tts].playback must be one of {sorted(_VALID_PLAYBACK)}, got {playback!r}"
        )
    if total_steps < 1:
        raise ValueError("[tts].total_steps must be >= 1")
    if speed <= 0:
        raise ValueError("[tts].speed must be > 0")
    if chime_pause_ms < 0:
        raise ValueError("[tts].chime_pause_ms must be >= 0")

    return TtsConfig(
        model=model,
        device=device,
        voice=voice,
        lang=lang,
        total_steps=total_steps,
        speed=speed,
        playback=playback,
        auto_download=auto_download,
        chime_before_speak=chime_before_speak,
        chime_pause_ms=chime_pause_ms,
        chime_file=chime_file,
    )


_VALID_LOAD_DTYPES = frozenset({"auto", "float16", "float32", "bfloat16"})


def _parse_summarize_table(raw: dict[str, object]) -> SummarizeConfig:
    model = str(raw.get("model", DEFAULT_MODEL_ID)).strip()
    if not model:
        raise ValueError("[summarize].model must be non-empty")
    backend = str(raw.get("backend", "transformers")).lower()
    ollama_host = str(raw.get("ollama_host", "http://localhost:11434")).strip()
    if backend not in _VALID_SUMMARIZE_BACKENDS:
        raise ValueError(
            f"[summarize].backend must be one of {sorted(_VALID_SUMMARIZE_BACKENDS)}, "
            f"got {backend!r}"
        )
    if not ollama_host:
        raise ValueError("[summarize].ollama_host must be non-empty")
    device = _normalize_device(str(raw.get("device", "auto")), section="summarize")
    cpu_threads = int(raw.get("cpu_threads", 0))
    idle_unload_minutes = int(raw.get("idle_unload_minutes", 10))
    chat_max_new_tokens = int(raw.get("chat_max_new_tokens", CHAT_LM_MAX_NEW_TOKENS))
    load_dtype = str(raw.get("load_dtype", "auto")).lower()
    chat_input_format = str(raw.get("chat_input_format", "plain")).lower()
    if cpu_threads < 0:
        raise ValueError("[summarize].cpu_threads must be >= 0")
    if idle_unload_minutes < 0:
        raise ValueError("[summarize].idle_unload_minutes must be >= 0")
    if chat_max_new_tokens < 8:
        raise ValueError("[summarize].chat_max_new_tokens must be >= 8")
    if load_dtype not in _VALID_LOAD_DTYPES:
        raise ValueError(
            f"[summarize].load_dtype must be one of {sorted(_VALID_LOAD_DTYPES)}, "
            f"got {load_dtype!r}"
        )
    if chat_input_format not in _VALID_CHAT_INPUT_FORMATS:
        raise ValueError(
            f"[summarize].chat_input_format must be one of "
            f"{sorted(_VALID_CHAT_INPUT_FORMATS)}, got {chat_input_format!r}"
        )
    return SummarizeConfig(
        model=model,
        backend=backend,
        ollama_host=ollama_host,
        device=device,
        cpu_threads=cpu_threads,
        idle_unload_minutes=idle_unload_minutes,
        chat_max_new_tokens=chat_max_new_tokens,
        load_dtype=load_dtype,
        chat_input_format=chat_input_format,
    )


def _parse_speech_table(raw: dict[str, object]) -> SpeechConfig:
    mode = str(raw.get("mode", "auto")).lower()
    target_lang = str(raw.get("target_lang", "en"))

    if mode not in _VALID_SPEECH_MODES:
        raise ValueError(
            f"[speech].mode must be one of {sorted(_VALID_SPEECH_MODES)}, got {mode!r}"
        )

    return SpeechConfig(mode=mode, target_lang=target_lang)


def _apply_tts_env(cfg: TtsConfig) -> TtsConfig:
    model = _env_str("VOXPOST_TTS_MODEL") or cfg.model
    if model not in _VALID_TTS_MODELS:
        raise ValueError(
            f"VOXPOST_TTS_MODEL must be one of {sorted(_VALID_TTS_MODELS)}, got {model!r}"
        )
    device_raw = _env_str("VOXPOST_TTS_DEVICE")
    device = _normalize_device(device_raw, section="tts") if device_raw else cfg.device
    voice = _env_str("VOXPOST_TTS_VOICE") or cfg.voice
    lang = _env_str("VOXPOST_TTS_LANG") or cfg.lang
    total_steps = _env_int("VOXPOST_TTS_TOTAL_STEPS")
    speed = _env_float("VOXPOST_TTS_SPEED")
    playback = _env_str("VOXPOST_TTS_PLAYBACK")
    auto_download = _env_bool("VOXPOST_TTS_AUTO_DOWNLOAD")
    chime_before_speak = _env_bool("VOXPOST_TTS_CHIME")
    chime_pause_ms = _env_int("VOXPOST_TTS_CHIME_PAUSE_MS")
    chime_file = _env_str("VOXPOST_TTS_CHIME_FILE")

    if playback is not None:
        playback = playback.lower()
        if playback not in _VALID_PLAYBACK:
            raise ValueError(
                f"VOXPOST_TTS_PLAYBACK must be one of {sorted(_VALID_PLAYBACK)}, "
                f"got {playback!r}"
            )

    return TtsConfig(
        model=model,
        device=device,
        voice=voice,
        lang=lang,
        total_steps=total_steps if total_steps is not None else cfg.total_steps,
        speed=speed if speed is not None else cfg.speed,
        playback=playback if playback is not None else cfg.playback,
        auto_download=auto_download if auto_download is not None else cfg.auto_download,
        chime_before_speak=(
            chime_before_speak if chime_before_speak is not None else cfg.chime_before_speak
        ),
        chime_pause_ms=chime_pause_ms if chime_pause_ms is not None else cfg.chime_pause_ms,
        chime_file=chime_file if chime_file is not None else cfg.chime_file,
    )


def _apply_summarize_env(cfg: SummarizeConfig) -> SummarizeConfig:
    model = _env_str("VOXPOST_SUMMARIZER_MODEL") or cfg.model
    backend = _env_str("VOXPOST_SUMMARIZER_BACKEND")
    if backend is not None:
        backend = backend.lower()
        if backend not in _VALID_SUMMARIZE_BACKENDS:
            raise ValueError(
                f"VOXPOST_SUMMARIZER_BACKEND must be one of "
                f"{sorted(_VALID_SUMMARIZE_BACKENDS)}, got {backend!r}"
            )
    ollama_host = _env_str("VOXPOST_OLLAMA_HOST") or cfg.ollama_host
    device_raw = _env_str("VOXPOST_SUMMARIZER_DEVICE")
    device = (
        _normalize_device(device_raw, section="summarize") if device_raw else cfg.device
    )
    cpu_threads = _env_int("VOXPOST_SUMMARIZER_CPU_THREADS")
    idle_unload_minutes = _env_int("VOXPOST_SUMMARIZER_IDLE_UNLOAD_MINUTES")
    chat_max_new_tokens = _env_int("VOXPOST_SUMMARIZER_MAX_NEW_TOKENS")
    load_dtype = _env_str("VOXPOST_SUMMARIZER_LOAD_DTYPE")
    chat_input_format = _env_str("VOXPOST_SUMMARIZER_INPUT")
    if load_dtype is not None:
        load_dtype = load_dtype.lower()
        if load_dtype not in _VALID_LOAD_DTYPES:
            raise ValueError(
                f"VOXPOST_SUMMARIZER_LOAD_DTYPE must be one of "
                f"{sorted(_VALID_LOAD_DTYPES)}, got {load_dtype!r}"
            )
    if chat_input_format is not None:
        chat_input_format = chat_input_format.lower()
        if chat_input_format not in _VALID_CHAT_INPUT_FORMATS:
            raise ValueError(
                f"VOXPOST_SUMMARIZER_INPUT must be one of "
                f"{sorted(_VALID_CHAT_INPUT_FORMATS)}, got {chat_input_format!r}"
            )
    return SummarizeConfig(
        model=model,
        backend=backend if backend is not None else cfg.backend,
        ollama_host=ollama_host,
        device=device,
        cpu_threads=cpu_threads if cpu_threads is not None else cfg.cpu_threads,
        idle_unload_minutes=(
            idle_unload_minutes if idle_unload_minutes is not None else cfg.idle_unload_minutes
        ),
        chat_max_new_tokens=(
            chat_max_new_tokens if chat_max_new_tokens is not None else cfg.chat_max_new_tokens
        ),
        load_dtype=load_dtype if load_dtype is not None else cfg.load_dtype,
        chat_input_format=(
            chat_input_format if chat_input_format is not None else cfg.chat_input_format
        ),
    )


def _apply_speech_env(cfg: SpeechConfig) -> SpeechConfig:
    mode = _env_str("VOXPOST_SPEECH_LANG_MODE") or cfg.mode
    mode = mode.lower()
    if mode not in _VALID_SPEECH_MODES:
        raise ValueError(
            f"VOXPOST_SPEECH_LANG_MODE must be one of {sorted(_VALID_SPEECH_MODES)}, "
            f"got {mode!r}"
        )
    target_lang = _env_str("VOXPOST_SPEECH_TARGET_LANG") or cfg.target_lang
    return SpeechConfig(mode=mode, target_lang=target_lang)


def load_user_config(config_dir: Path | None = None) -> VoxpostUserConfig:
    """
    Load user settings from ``voxpost.toml`` under the config directory.

    Missing file → built-in defaults. Environment variables override TOML.
    """
    base = config_dir or _default_config_dir()
    path = base / CONFIG_FILENAME
    if not path.is_file():
        legacy = base / "mailcue.toml"
        if legacy.is_file():
            path = legacy
    tts = TtsConfig()
    speech = SpeechConfig()
    summarize = SummarizeConfig()

    if path.is_file():
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if "tts" in data:
            tts = _parse_tts_table(data["tts"])
        if "speech" in data:
            speech = _parse_speech_table(data["speech"])
        if "summarize" in data:
            summarize = _parse_summarize_table(data["summarize"])

    tts = _apply_tts_env(tts)
    speech = _apply_speech_env(speech)
    summarize = _apply_summarize_env(summarize)

    return VoxpostUserConfig(
        tts=tts,
        speech=speech,
        summarize=summarize,
        config_path=path if path.is_file() else None,
    )


def resolved_speakable_lang(config_dir: Path | None = None) -> str:
    """
    Language for speakable lines and number spelling.

    Always comes from voxpost.toml — never inferred from the email body.
    ``fixed`` → ``[speech].target_lang``; ``auto`` → ``[tts].lang``.
    """
    cfg = load_user_config(config_dir)
    if cfg.speech.mode == "fixed":
        return cfg.speech.target_lang.strip().lower() or cfg.tts.lang
    return cfg.tts.lang.strip().lower() or "en"
