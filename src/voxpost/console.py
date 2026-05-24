"""Human-friendly terminal output for ``voxpost listen`` and related CLI flows."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import TextIO

import click

from voxpost.ascii_logo import print_voxpost_logo

_SYMBOL = {
    "info": "●",
    "wait": "○",
    "ping": "↓",
    "mail": "✉",
    "think": "◆",
    "speak": "♪",
    "ok": "✓",
    "warn": "⚠",
    "err": "✗",
}

_QUIET_LOGGERS = (
    "google",
    "googleapiclient",
    "urllib3",
    "grpc",
    "httpx",
    "httpcore",
    "transformers",
    "torch",
    "filelock",
    "huggingface_hub",
)


def _time_prefix() -> str:
    return click.style(datetime.now().strftime("%H:%M:%S") + "  ", dim=True)


def _truncate(text: str, max_len: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _display_sender(from_address: str | None) -> str:
    if not from_address:
        return "Unknown sender"
    raw = from_address.strip()
    if "<" in raw and ">" in raw:
        name = raw.split("<", 1)[0].strip().strip('"')
        if name:
            return name
        return raw.split("<", 1)[1].rstrip(">").strip()
    return raw


class ListenConsole:
    """Structured, readable stderr UI for the listen daemon."""

    def __init__(
        self,
        *,
        json_mode: bool = False,
        stream: TextIO | None = None,
    ) -> None:
        self.json_mode = json_mode
        self._stream = stream or sys.stderr

    def _echo(self, text: str = "", *, nl: bool = True) -> None:
        click.echo(text, file=self._stream, nl=nl)

    def _line(
        self,
        symbol: str,
        message: str,
        *,
        color: str | None = None,
        bold: bool = False,
        dim: bool = False,
    ) -> None:
        sym = click.style(f"{symbol} ", fg="cyan") if symbol else ""
        body = click.style(message, fg=color, bold=bold, dim=dim)
        self._echo(_time_prefix() + sym + body)

    def blank(self) -> None:
        self._echo()

    def section(self, title: str) -> None:
        self.blank()
        self._echo(click.style(f"  {title}", fg="cyan", bold=True))
        self._echo(click.style("  " + "─" * max(len(title), 20), fg="cyan", dim=True))

    def logo(self) -> bool:
        """Print the block-art VOXPOST logo when the terminal is wide enough."""
        return print_voxpost_logo(self._stream)

    def banner(self, title: str = "Voxpost listen") -> None:
        if not self.logo():
            self.blank()
            self._echo(click.style(f"  {title}", fg="cyan", bold=True))
            self._echo(click.style("  " + "─" * max(len(title), 24), fg="cyan", dim=True))

    def kv(self, key: str, value: str) -> None:
        label = click.style(f"    {key:<16}", dim=True)
        self._echo(label + click.style(value, fg="white"))

    def hint(self, message: str) -> None:
        self._line(_SYMBOL["wait"], message, dim=True)

    def info(self, message: str) -> None:
        self._line(_SYMBOL["info"], message)

    def success(self, message: str) -> None:
        self._line(_SYMBOL["ok"], message, color="green")

    def warn(self, message: str) -> None:
        self._line(_SYMBOL["warn"], message, color="yellow")

    def error(self, message: str) -> None:
        self._line(_SYMBOL["err"], message, color="red", bold=True)

    def waiting(self) -> None:
        self.blank()
        self.hint("Waiting for new inbox mail — press Ctrl+C to stop.")
        self.blank()

    def startup_ready(
        self,
        *,
        account: str,
        project: str,
        subscription: str,
        summarize: bool,
        speak: bool,
        summarize_backend: str | None = None,
        summarize_model: str | None = None,
        speech_lang: str | None = None,
        tts_model: str | None = None,
        tts_device: str | None = None,
    ) -> None:
        self.section("Listen")
        self.kv("Gmail account", account)
        self.kv("GCP project", project)
        self.kv("Pub/Sub sub", _truncate(subscription, 56))
        if summarize:
            backend = summarize_backend or "transformers"
            model = summarize_model or "(default)"
            self.kv("Summarizer", f"{backend} · {model}")
            if speech_lang:
                self.kv("Speech language", speech_lang)
        if speak:
            tts = tts_model or "supertonic-3"
            device = tts_device or "auto"
            self.kv("TTS", f"{tts} · {device}")
        self.info("Gmail inbox watch registered")
        self.info("Pub/Sub listener connected")
        if speak:
            self.hint("Warming up TTS in the background (first chime may take a few seconds).")
        elif summarize:
            self.hint("Summarizer loads on first new mail (may take a minute on CPU).")

    def gmail_notification(self, history_id: str) -> None:
        self.blank()
        self._line(
            _SYMBOL["ping"],
            f"Gmail activity detected — checking history from {history_id}",
            color="blue",
        )

    def history_fetch(self, count: int) -> None:
        if count == 0:
            self.hint("No new inbox messages in this batch.")
            return
        noun = "message" if count == 1 else "messages"
        self.info(f"Found {count} new inbox {noun}")

    def raw_mail(self, event) -> None:
        """Block 1 only — no summarizer."""
        sender = _display_sender(getattr(event, "from_address", None))
        subject = _truncate(getattr(event, "subject", None) or "(no subject)", 72)
        self._line(_SYMBOL["mail"], f"{sender} · {subject}", bold=True)

    def mail_header(self, event) -> None:
        sender = _display_sender(getattr(event, "from_address", None))
        subject = _truncate(getattr(event, "subject", None) or "(no subject)", 72)
        self._line(_SYMBOL["mail"], f"{sender} · {subject}", bold=True)

    def summarizer_loading(self, backend: str, model: str) -> None:
        self._line(
            _SYMBOL["think"],
            f"Loading summarizer ({backend} · {model}) — first run can take a minute",
            dim=True,
        )

    def summarizing(self, backend: str, model: str) -> None:
        self._line(
            _SYMBOL["think"],
            f"Summarizing ({backend} · {model})…",
            color="magenta",
        )

    def speakable(self, line: str) -> None:
        self.blank()
        self._echo(click.style("    Speakable line", dim=True))
        wrapped = line.strip()
        self._echo(click.style(f"    {wrapped}", fg="green", bold=True))
        self.blank()

    def speaking(self) -> None:
        self._line(_SYMBOL["speak"], "Speaking aloud (chime → briefing)…", color="cyan")

    def spoke(self) -> None:
        self.success("Playback finished")

    def emit_json(self, payload: str) -> None:
        if self.json_mode:
            print(payload, flush=True)

    def shutdown(self) -> None:
        self.blank()
        self.info("Stopping — releasing Gmail watch and Pub/Sub listener")
        self.success("Voxpost listen stopped. Goodbye.")
        self.blank()


class _ConsoleLogHandler(logging.Handler):
    """Route voxpost log records through ListenConsole in normal mode."""

    def __init__(self, console: ListenConsole, *, verbose: bool) -> None:
        super().__init__()
        self._console = console
        self._verbose = verbose

    def emit(self, record: logging.LogRecord) -> None:
        if self._verbose:
            level_color = {
                logging.DEBUG: None,
                logging.INFO: None,
                logging.WARNING: "yellow",
                logging.ERROR: "red",
                logging.CRITICAL: "red",
            }.get(record.levelno)
            msg = record.getMessage()
            if record.levelno >= logging.ERROR:
                self._console.error(f"{record.name}: {msg}")
            elif record.levelno >= logging.WARNING:
                self._console.warn(f"{record.name}: {msg}")
            else:
                self._console._line(
                    _SYMBOL["info"],
                    f"{record.name}: {msg}",
                    color=level_color,
                    dim=record.levelno == logging.DEBUG,
                )
            return

        if record.levelno < logging.WARNING:
            return
        if record.levelno >= logging.ERROR:
            self._console.error(record.getMessage())
        else:
            self._console.warn(record.getMessage())


def setup_listen_logging(console: ListenConsole, *, verbose: bool = False) -> None:
    """Configure logging for ``voxpost listen`` — quiet libraries, readable voxpost output."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    handler = _ConsoleLogHandler(console, verbose=verbose)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.addHandler(handler)

    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING if verbose else logging.ERROR)


def describe_listen_modes(*, summarize: bool, speak: bool) -> str:
    if speak:
        return "full pipeline: detect → summarize → speak locally"
    if summarize:
        return "detect → summarize locally (no TTS)"
    return "detect new inbox mail only (Block 1)"


def _model_setup_hint(*, summarize: bool, speak: bool) -> str | None:
    if not summarize:
        return None
    from voxpost.config import _default_config_dir
    from voxpost.summarize import resolved_model_id

    model = resolved_model_id(_default_config_dir())
    steps = [f"ollama pull {model}"]
    if speak:
        steps.append("voxpost tts download")
    return "Need models? Run: " + " and ".join(steps)


def print_listen_intro(*, summarize: bool, speak: bool, json_mode: bool) -> None:
    """Short intro before the daemon starts (CLI layer)."""
    mode = describe_listen_modes(summarize=summarize, speak=speak)
    console = ListenConsole(json_mode=json_mode)
    console.logo()
    console.section("Starting")
    console.kv("Mode", mode)
    if json_mode:
        console.kv("Output", "JSON events on stdout")
    else:
        console.kv("Output", "Human-readable log on stderr")
    hint = _model_setup_hint(summarize=summarize, speak=speak)
    if hint:
        console.hint(hint)
    console.blank()
