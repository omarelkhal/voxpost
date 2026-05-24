"""Extract plain-text body from Gmail API message payloads."""

from __future__ import annotations

import base64
from typing import Any

DEFAULT_MAX_BODY_BYTES = 20_000


def _decode_data(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    return raw.decode("utf-8", errors="replace")


def _plain_text_from_part(part: dict[str, Any]) -> str | None:
    mime = part.get("mimeType", "")
    body = part.get("body") or {}
    data = body.get("data")
    if mime == "text/plain" and data:
        return _decode_data(data)
    for child in part.get("parts") or []:
        text = _plain_text_from_part(child)
        if text:
            return text
    return None


def extract_plain_text_body(payload: dict[str, Any] | None) -> str:
    """Return the first text/plain part, or decode a single-part body."""
    if not payload:
        return ""

    text = _plain_text_from_part(payload)
    if text is not None:
        return text

    data = (payload.get("body") or {}).get("data")
    if data:
        return _decode_data(data)
    return ""


def cap_body_text(body: str, max_bytes: int = DEFAULT_MAX_BODY_BYTES) -> tuple[str, bool]:
    """Truncate body to max_bytes (UTF-8). Returns (text, was_truncated)."""
    encoded = body.encode("utf-8")
    if len(encoded) <= max_bytes:
        return body, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated, True
