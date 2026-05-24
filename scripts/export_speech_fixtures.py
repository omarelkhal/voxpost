#!/usr/bin/env python3
"""Export legacy monolithic speech_check_cases module to per-case JSON files."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LEGACY = ROOT / "scripts" / "_legacy_speech_check_cases.py"
OUT = ROOT / "src" / "voxpost" / "speech_check" / "fixtures"


def _serialize_event(event) -> dict:
    attachments = [
        {
            "filename": a.filename,
            "mime_type": a.mime_type,
            **({"size_bytes": a.size_bytes} if a.size_bytes is not None else {}),
        }
        for a in event.attachments
    ]
    return {
        "account_id": event.account_id,
        "message_id": event.message_id,
        "thread_id": event.thread_id,
        "history_id": event.history_id,
        "from_address": event.from_address,
        "subject": event.subject,
        "body": event.body,
        "has_attachments": event.has_attachments,
        "attachment_count": event.attachment_count,
        "attachments": attachments,
    }


def _load_legacy():
    if not LEGACY.is_file():
        raise SystemExit(
            f"Missing {LEGACY}. Run:\n"
            f"  git show 9713573:src/voxpost/speech_check_cases.py > {LEGACY}"
        )
    sys.path.insert(0, str(SRC))
    spec = importlib.util.spec_from_file_location("legacy_speech_check_cases", LEGACY)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {LEGACY}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = _load_legacy()
    cases = mod.speech_check_cases()
    OUT.mkdir(parents=True, exist_ok=True)
    for case in cases:
        payload = {
            "case_id": case.case_id,
            "label": case.label,
            "intent": case.intent,
            "must_mention_any": list(case.must_mention_any),
            "must_not_mention": list(case.must_not_mention),
            "max_words": case.max_words,
            "event": _serialize_event(case.event),
        }
        path = OUT / f"{case.case_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(path.name)
    manifest = {
        "suite_version": 1,
        "case_ids": [c.case_id for c in cases],
        "count": len(cases),
    }
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(cases)} fixtures to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
