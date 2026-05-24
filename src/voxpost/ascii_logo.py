"""VOXPOST block-letter logo for terminal startup."""

from __future__ import annotations

import shutil
import sys
from typing import TextIO

import click

# Block-art "VOXPOST" (gradient-friendly ░▒▓█ characters).
VOXPOST_LOGO: tuple[str, ...] = (
    "░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░ ░▒▓███████▓▒░▒▓████████▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░         ░▒▓█▓▒░",
    " ░▒▓█▓▒▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░         ░▒▓█▓▒░",
    " ░▒▓█▓▒▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░   ░▒▓█▓▒░",
    "  ░▒▓█▓▓█▓▒░ ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░",
    "  ░▒▓█▓▓█▓▒░ ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░",
    "   ░▒▓██▓▒░   ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░       ░▒▓██████▓▒░░▒▓███████▓▒░   ░▒▓█▓▒░",
)

_LOGO_MIN_WIDTH = max(len(line) for line in VOXPOST_LOGO) + 2

_BLOCK_STYLES: dict[str, tuple[str, bool]] = {
    "░": ("bright_black", False),
    "▒": ("blue", False),
    "▓": ("cyan", False),
    "█": ("bright_cyan", True),
}


def logo_fits_terminal(min_width: int | None = None) -> bool:
    needed = min_width if min_width is not None else _LOGO_MIN_WIDTH
    try:
        return shutil.get_terminal_size(fallback=(120, 24)).columns >= needed
    except OSError:
        return True


def style_logo_line(line: str) -> str:
    """Apply a cyan gradient to block characters; leave spaces plain."""
    parts: list[str] = []
    for char in line:
        spec = _BLOCK_STYLES.get(char)
        if spec is None:
            parts.append(char)
        else:
            color, bold = spec
            parts.append(click.style(char, fg=color, bold=bold))
    return "".join(parts)


def print_voxpost_logo(
    stream: TextIO | None = None,
    *,
    color: bool = True,
) -> bool:
    """
    Print the VOXPOST ASCII logo.

    Returns True if the logo was printed, False if skipped (narrow terminal or non-TTY).
    """
    out = stream or sys.stderr
    if not logo_fits_terminal():
        return False
    use_color = color and getattr(out, "isatty", lambda: False)()
    click.echo("", file=out)
    for line in VOXPOST_LOGO:
        text = style_logo_line(line) if use_color else line
        click.echo(text, file=out)
    click.echo("", file=out)
    return True
