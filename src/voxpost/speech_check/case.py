"""Speech-check case model."""

from __future__ import annotations

from dataclasses import dataclass

from voxpost.events import NewMailEvent


@dataclass(frozen=True)
class SpeechCheckCase:
    case_id: str
    label: str
    intent: str
    event: NewMailEvent
    input_lang: str = "en"
    must_mention_any: tuple[str, ...] = ()
    must_not_mention: tuple[str, ...] = ()
    max_words: int = 40
