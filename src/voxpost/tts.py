"""Block 4 — local Supertonic TTS with on-device playback."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_VOICE_NAME = "M1"
DEFAULT_TTS_MODEL = "supertonic-3"
DEFAULT_LANG = "en"
DEFAULT_TOTAL_STEPS = 8
DEFAULT_SPEED = 1.05
DEFAULT_CHIME_BEFORE_SPEAK = True
DEFAULT_CHIME_PAUSE_MS = 350
DEFAULT_CHIME_SAMPLE_RATE = 22050

_TTS_IMPORT_ERROR = (
    "TTS requires optional dependencies. Install with:\n"
    "  pip install 'voxpost[tts]'"
)


class Speaker(Protocol):
    """Minimal interface for listen tests and future UI injection."""

    def speak(self, text: str) -> None: ...


def resolve_playback() -> str:
    """Return ``sounddevice``, ``aplay``, or empty if no backend is available."""
    try:
        import sounddevice as sd  # noqa: F401
    except (ImportError, OSError):
        pass
    else:
        return "sounddevice"
    if shutil.which("aplay"):
        return "aplay"
    return ""


def resolve_onnx_providers(device: str = "auto") -> list[str]:
    """
    Map ``auto`` | ``cpu`` | ``cuda`` | ``gpu`` to ONNX Runtime execution providers.

    ``auto`` uses CUDA when ``onnxruntime-gpu`` is installed, else CPU.
    """
    try:
        import onnxruntime as ort
    except ImportError:
        return ["CPUExecutionProvider"]

    available = set(ort.get_available_providers())
    choice = device.strip().lower()
    if choice == "gpu":
        choice = "cuda"

    if choice == "auto":
        if "CUDAExecutionProvider" in available:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    if choice == "cuda":
        if "CUDAExecutionProvider" in available:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        logger.warning("CUDA requested for TTS but CUDAExecutionProvider is unavailable")
        return ["CPUExecutionProvider"]

    if choice != "cpu":
        raise ValueError(f"unsupported TTS device {device!r}")
    return ["CPUExecutionProvider"]


def _configure_supertonic_providers(device: str) -> None:
    """Patch Supertonic's provider list in-place before model load."""
    import supertonic.config as st_cfg

    providers = resolve_onnx_providers(device)
    st_cfg.DEFAULT_ONNX_PROVIDERS[:] = providers
    logger.info("Supertonic ONNX providers: %s", providers)


def synthesize_chime(*, sample_rate: int = DEFAULT_CHIME_SAMPLE_RATE) -> Any:
    """Short two-tone chime — new-mail cue before TTS."""
    import numpy as np

    def tone(freq: float, duration_s: float, *, volume: float = 0.28) -> Any:
        count = max(1, int(sample_rate * duration_s))
        t = np.arange(count, dtype=np.float32) / sample_rate
        wave = volume * np.sin(2 * np.pi * freq * t)
        fade = np.linspace(1.0, 0.0, count, dtype=np.float32)
        return wave * fade

    gap = np.zeros(int(sample_rate * 0.04), dtype=np.float32)
    audio = np.concatenate([tone(880.0, 0.11), gap, tone(1174.7, 0.16)])
    return audio.astype(np.float32)


def load_chime_audio(path: str | Path, *, sample_rate: int | None = None) -> tuple[Any, int]:
    """Load a custom WAV/FLAC chime; resample to ``sample_rate`` when given."""
    import numpy as np

    try:
        import soundfile as sf
    except ImportError as err:
        raise RuntimeError(_TTS_IMPORT_ERROR) from err

    audio, file_rate = sf.read(str(path), dtype="float32", always_2d=False)
    mono = np.asarray(audio, dtype=np.float32).squeeze()
    if mono.ndim > 1:
        mono = mono.mean(axis=1)
    target_rate = sample_rate or file_rate
    if file_rate != target_rate and mono.size:
        indices = np.linspace(0, mono.size - 1, int(mono.size * target_rate / file_rate))
        mono = np.interp(indices, np.arange(mono.size), mono).astype(np.float32)
    return mono, int(target_rate)


def play_notification_chime(
    *,
    backend: str | None = None,
    chime_file: str | None = None,
) -> None:
    """Play the mail-arrival chime; no-op when no playback backend is available."""
    resolved = backend or resolve_playback()
    if not resolved:
        logger.debug("Skipping notification chime — no playback backend")
        return
    if chime_file:
        audio, sample_rate = load_chime_audio(chime_file)
    else:
        sample_rate = DEFAULT_CHIME_SAMPLE_RATE
        audio = synthesize_chime(sample_rate=sample_rate)
    play_audio_blocking(audio, sample_rate, resolved)


def speak_with_chime(
    speaker: SupertonicSpeaker,
    text: str,
    *,
    chime_before_speak: bool = DEFAULT_CHIME_BEFORE_SPEAK,
    chime_pause_ms: int = DEFAULT_CHIME_PAUSE_MS,
    chime_file: str | None = None,
) -> None:
    """Synthesize speech first, then chime + brief pause, then play (tight cue-to-voice gap)."""
    line = text.strip()
    if not line:
        raise ValueError("text must be non-empty")

    backend = speaker._playback_backend
    if backend is None:
        backend = resolve_playback()
    if not backend:
        raise RuntimeError(
            "No audio playback backend available. Install sounddevice or use "
            "Linux with aplay installed."
        )

    audio, sample_rate = speaker.synthesize(line)

    if chime_before_speak:
        try:
            play_notification_chime(
                backend=backend,
                chime_file=chime_file,
            )
            if chime_pause_ms > 0:
                time.sleep(chime_pause_ms / 1000.0)
        except Exception:
            logger.exception("Notification chime failed (continuing to TTS)")

    play_audio_blocking(audio, sample_rate, backend)


def play_audio_blocking(
    audio: Any,
    sample_rate: int,
    backend: str,
) -> None:
    """Play mono float32 audio using the chosen backend."""
    import numpy as np

    if np.asarray(audio).size == 0:
        return
    mono = np.asarray(audio, dtype=np.float32).squeeze()
    if backend == "sounddevice":
        import sounddevice as sd

        sd.play(mono, sample_rate, blocking=True)
        return
    if backend == "aplay":
        import soundfile as sf

        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            sf.write(path, mono, sample_rate, subtype="PCM_16")
            subprocess.run(["aplay", "-q", path], check=False)
        finally:
            if os.path.isfile(path):
                os.unlink(path)
        return
    raise RuntimeError(f"unknown playback backend: {backend}")


class SupertonicSpeaker:
    """Lazy-loaded Supertonic 3 synthesizer with local playback."""

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_TTS_MODEL,
        device: str = "auto",
        voice_name: str = DEFAULT_VOICE_NAME,
        lang: str = DEFAULT_LANG,
        total_steps: int = DEFAULT_TOTAL_STEPS,
        speed: float = DEFAULT_SPEED,
        auto_download: bool = True,
        playback_backend: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._voice_name = voice_name
        self._lang = lang
        self._total_steps = total_steps
        self._speed = speed
        self._auto_download = auto_download
        self._playback_backend = playback_backend
        self._engine: Any | None = None
        self._voice_style: Any | None = None

    @property
    def voice_name(self) -> str:
        return self._voice_name

    @property
    def lang(self) -> str:
        return self._lang

    def _ensure_loaded(self) -> None:
        if self._engine is not None and self._voice_style is not None:
            return
        try:
            from supertonic import TTS
        except ImportError as err:
            raise RuntimeError(_TTS_IMPORT_ERROR) from err

        logger.info(
            "Loading Supertonic TTS (model=%s, device=%s, voice=%s, lang=%s)",
            self._model_name,
            self._device,
            self._voice_name,
            self._lang,
        )
        _configure_supertonic_providers(self._device)
        self._engine = TTS(model=self._model_name, auto_download=self._auto_download)
        self._voice_style = self._engine.get_voice_style(self._voice_name)

    def warmup(self) -> None:
        """Load model and voice style without synthesizing audio."""
        self._ensure_loaded()

    def download(self) -> Path:
        """Download Supertonic ONNX assets to the default cache directory."""
        try:
            from supertonic.loader import download_model, get_cache_dir
        except ImportError as err:
            raise RuntimeError(_TTS_IMPORT_ERROR) from err

        cache_dir = get_cache_dir()
        download_model(cache_dir)
        return cache_dir

    def synthesize(self, text: str) -> tuple[Any, int]:
        """Return mono float32 audio and sample rate without playing."""
        import numpy as np

        line = text.strip()
        if not line:
            raise ValueError("text must be non-empty")
        self._ensure_loaded()
        assert self._engine is not None
        assert self._voice_style is not None

        wav, _duration = self._engine.synthesize(
            line,
            voice_style=self._voice_style,
            lang=self._lang,
            total_steps=self._total_steps,
            speed=self._speed,
            verbose=False,
        )
        mono = np.asarray(wav, dtype=np.float32).squeeze()
        return mono, int(self._engine.sample_rate)

    def speak(self, text: str) -> None:
        """Synthesize ``text`` and play it locally."""
        line = text.strip()
        if not line:
            raise ValueError("text must be non-empty")

        backend = self._playback_backend
        if backend is None:
            backend = resolve_playback()
        if not backend:
            raise RuntimeError(
                "No audio playback backend available. Install sounddevice or use "
                "Linux with aplay installed."
            )

        audio, sample_rate = self.synthesize(line)
        play_audio_blocking(audio, sample_rate, backend)


def download_supertonic_models() -> Path:
    """Download Supertonic assets (CLI helper)."""
    return SupertonicSpeaker().download()


def test_speak(
    text: str,
    *,
    speaker: SupertonicSpeaker | None = None,
    config_dir: Path | None = None,
) -> None:
    """Speak one line for smoke testing."""
    (speaker or supertonic_speaker_from_user_config(config_dir)).speak(text)


def supertonic_speaker_from_user_config(
    config_dir: Path | None = None,
) -> SupertonicSpeaker:
    """Build a speaker from ``voxpost.toml`` (or defaults)."""
    from voxpost.user_config import load_user_config

    return supertonic_speaker_from_config(load_user_config(config_dir))


def supertonic_speaker_from_config(user_config) -> SupertonicSpeaker:
    """Build a speaker from a loaded :class:`~voxpost.user_config.VoxpostUserConfig`."""
    tts = user_config.tts
    return SupertonicSpeaker(
        model_name=tts.model,
        device=tts.device,
        voice_name=tts.voice,
        lang=tts.lang,
        total_steps=tts.total_steps,
        speed=tts.speed,
        auto_download=tts.auto_download,
        playback_backend=tts.playback_backend,
    )


def speak_from_user_config(
    text: str,
    *,
    speaker: SupertonicSpeaker | None = None,
    config_dir: Path | None = None,
) -> None:
    """Speak with chime settings from ``voxpost.toml``."""
    from voxpost.user_config import load_user_config

    cfg = load_user_config(config_dir)
    tts = cfg.tts
    resolved = speaker or supertonic_speaker_from_config(cfg)
    speak_with_chime(
        resolved,
        text,
        chime_before_speak=tts.chime_before_speak,
        chime_pause_ms=tts.chime_pause_ms,
        chime_file=tts.chime_file,
    )
