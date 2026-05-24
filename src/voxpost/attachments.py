"""Attachment metadata from Gmail message payloads — no content download."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AttachmentInfo:
    filename: str
    mime_type: str
    size_bytes: int | None = None


def _is_attachment_part(part: dict[str, Any]) -> bool:
    """True when Gmail treats this part as a file attachment (metadata only)."""
    filename = (part.get("filename") or "").strip()
    body = part.get("body") or {}
    if filename:
        return True
    return bool(body.get("attachmentId"))


def _part_to_attachment(part: dict[str, Any]) -> AttachmentInfo:
    filename = (part.get("filename") or "").strip()
    body = part.get("body") or {}
    if not filename:
        filename = "attachment"
    size = body.get("size")
    return AttachmentInfo(
        filename=filename,
        mime_type=part.get("mimeType") or "application/octet-stream",
        size_bytes=int(size) if size is not None else None,
    )


def extract_attachments(payload: dict[str, Any] | None) -> tuple[AttachmentInfo, ...]:
    """
    Walk the MIME tree and return attachment metadata.

    Does not call attachments.get — filenames and types only.
    """
    if not payload:
        return ()

    found: list[AttachmentInfo] = []

    def walk(part: dict[str, Any]) -> None:
        if _is_attachment_part(part):
            found.append(_part_to_attachment(part))
        for child in part.get("parts") or []:
            walk(child)

    walk(payload)
    return tuple(found)
