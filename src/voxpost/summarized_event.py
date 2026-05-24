"""Block 3 output — NewMailEvent plus one speakable summary line."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from voxpost.events import NewMailEvent


@dataclass(frozen=True)
class SummarizedMailEvent:
    """Ephemeral mail event with a one-line local summary for TTS (Block 4)."""

    mail: NewMailEvent
    speakable_line: str

    def to_json(self) -> str:
        payload = asdict(self.mail)
        payload["speakable_line"] = self.speakable_line
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def from_mail_event(event: NewMailEvent, speakable_line: str) -> SummarizedMailEvent:
        line = speakable_line.strip()
        if not line:
            raise ValueError("speakable_line must be non-empty")
        return SummarizedMailEvent(mail=event, speakable_line=line)
