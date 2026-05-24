"""Terminal console formatting for listen."""

from __future__ import annotations

import io

from voxpost.ascii_logo import VOXPOST_LOGO, logo_fits_terminal, print_voxpost_logo, style_logo_line
from voxpost.console import (
    ListenConsole,
    _model_setup_hint,
    describe_listen_modes,
    print_listen_intro,
)


def test_voxpost_logo_has_seven_lines():
    assert len(VOXPOST_LOGO) == 7
    assert all("▓" in line for line in VOXPOST_LOGO)


def test_style_logo_line_preserves_length():
    line = VOXPOST_LOGO[0]
    styled = style_logo_line(line)
    assert len(styled) >= len(line)


def test_print_voxpost_logo_to_buffer():
    buf = io.StringIO()
    assert print_voxpost_logo(buf, color=False) is True
    assert "VOXPOST" not in buf.getvalue()  # art is block chars, not letters
    assert "▓" in buf.getvalue()


def test_logo_fits_terminal():
    assert logo_fits_terminal(min_width=10) is True


def test_listen_console_speakable_writes_to_stderr():
    buf = io.StringIO()
    console = ListenConsole(json_mode=False, stream=buf)
    console.speakable("Alex says the deploy failed.")
    out = buf.getvalue()
    assert "Speakable line" in out
    assert "deploy failed" in out


def test_listen_console_json_mode_prints_stdout(capsys):
    console = ListenConsole(json_mode=True)
    console.emit_json('{"ok": true}')
    captured = capsys.readouterr()
    assert captured.out.strip() == '{"ok": true}'
    assert captured.err == ""


def test_describe_listen_modes():
    assert "speak" in describe_listen_modes(summarize=True, speak=True)
    assert describe_listen_modes(summarize=False, speak=False).startswith("detect")


def test_print_listen_intro_ollama_hint_only():
    hint = _model_setup_hint(summarize=True, speak=True)
    assert hint is not None
    assert "ollama pull" in hint
    assert "summarize download" not in hint
    assert "voxpost tts download" in hint


def test_print_listen_intro_runs_without_error():
    print_listen_intro(summarize=True, speak=True, json_mode=False)
