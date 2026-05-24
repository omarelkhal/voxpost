"""Load speech-check email fixtures from individual JSON files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from voxpost.attachments import AttachmentInfo
from voxpost.events import NewMailEvent
from voxpost.speech_check.case import SpeechCheckCase
from voxpost.speech_langs import infer_fixture_input_lang

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def default_fixtures_dir() -> Path:
    return _FIXTURES_DIR


def list_fixture_ids(*, fixtures_dir: Path | None = None) -> tuple[str, ...]:
    """Sorted case_id list from ``*.json`` files in the fixtures directory."""
    root = fixtures_dir or _FIXTURES_DIR
    if not root.is_dir():
        return ()
    ids: list[str] = []
    for path in sorted(root.glob("*.json")):
        if path.name.startswith("_"):
            continue
        ids.append(path.stem)
    return tuple(ids)


def _parse_event(raw: dict[str, object]) -> NewMailEvent:
    attachments_raw = raw.get("attachments") or []
    attachments: tuple[AttachmentInfo, ...] = tuple(
        AttachmentInfo(
            filename=str(item["filename"]),
            mime_type=str(item.get("mime_type", "application/octet-stream")),
            size_bytes=int(item["size_bytes"]) if item.get("size_bytes") is not None else None,
        )
        for item in attachments_raw
        if isinstance(item, dict)
    )
    has_attachments = bool(raw.get("has_attachments", attachments))
    attachment_count = int(raw.get("attachment_count", len(attachments)))

    return NewMailEvent(
        account_id=str(raw.get("account_id", "eval@test.local")),
        message_id=str(raw.get("message_id", "eval-msg")),
        thread_id=str(raw.get("thread_id", "eval-thread")),
        history_id=str(raw.get("history_id", "1")),
        from_address=str(raw.get("from_address", "")),
        subject=str(raw.get("subject", "")),
        body=str(raw.get("body", "")),
        has_attachments=has_attachments,
        attachment_count=attachment_count,
        attachments=attachments,
    )


def load_fixture(path: Path) -> SpeechCheckCase:
    data = json.loads(path.read_text(encoding="utf-8"))
    case_id = str(data.get("case_id", path.stem))
    explicit_lang = data.get("input_lang")
    return SpeechCheckCase(
        case_id=case_id,
        label=str(data["label"]),
        intent=str(data["intent"]),
        event=_parse_event(data["event"]),
        input_lang=infer_fixture_input_lang(
            case_id,
            str(explicit_lang) if explicit_lang is not None else None,
        ),
        must_mention_any=tuple(str(x) for x in data.get("must_mention_any", ())),
        must_not_mention=tuple(str(x) for x in data.get("must_not_mention", ())),
        max_words=int(data.get("max_words", 40)),
    )


def load_fixture_by_id(case_id: str, *, fixtures_dir: Path | None = None) -> SpeechCheckCase:
    """Load one shipped fixture by ``case_id`` (stem of ``fixtures/{case_id}.json``)."""
    root = fixtures_dir or _FIXTURES_DIR
    path = root / f"{case_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Speech-check fixture not found: {path}")
    return load_fixture(path)


@lru_cache(maxsize=1)
def load_fixtures(fixtures_dir: str | None = None) -> tuple[SpeechCheckCase, ...]:
    root = Path(fixtures_dir) if fixtures_dir else _FIXTURES_DIR
    paths = [root / f"{case_id}.json" for case_id in list_fixture_ids(fixtures_dir=root)]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing speech-check fixture file(s): "
            + ", ".join(p.name for p in missing)
        )
    return tuple(load_fixture(p) for p in paths)
