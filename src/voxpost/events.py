"""Ephemeral new-mail event emitted by the Block 1 pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from voxpost.attachments import AttachmentInfo


@dataclass(frozen=True)
class NewMailEvent:
    account_id: str
    message_id: str
    thread_id: str
    history_id: str
    received_at: str | None = None
    from_address: str | None = None
    subject: str | None = None
    body: str | None = None
    body_truncated: bool = False
    has_attachments: bool = False
    attachment_count: int = 0
    attachments: tuple[AttachmentInfo, ...] = ()

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def log_line(self) -> str:
        """Human-readable line for stdout (may include from/subject)."""
        parts = [f"NewMailEvent message_id={self.message_id}"]
        if self.from_address:
            parts.append(f"from={self.from_address!r}")
        if self.subject:
            parts.append(f"subject={self.subject!r}")
        if self.has_attachments:
            names = ", ".join(a.filename for a in self.attachments)
            parts.append(f"attachments({self.attachment_count})={names!r}")
        return " ".join(parts)

    @classmethod
    def from_dict(cls, data: dict) -> NewMailEvent:
        attachments_raw = data.get("attachments") or []
        attachments = tuple(
            AttachmentInfo(
                filename=item["filename"],
                mime_type=item.get("mime_type", "application/octet-stream"),
                size_bytes=item.get("size_bytes"),
            )
            for item in attachments_raw
        )
        return cls(
            account_id=data["account_id"],
            message_id=data["message_id"],
            thread_id=data["thread_id"],
            history_id=data["history_id"],
            received_at=data.get("received_at"),
            from_address=data.get("from_address"),
            subject=data.get("subject"),
            body=data.get("body"),
            body_truncated=bool(data.get("body_truncated", False)),
            has_attachments=bool(data.get("has_attachments", False)),
            attachment_count=int(data.get("attachment_count", len(attachments))),
            attachments=attachments,
        )

    @classmethod
    def from_json(cls, raw: str) -> NewMailEvent:
        return cls.from_dict(json.loads(raw))
