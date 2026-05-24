"""Persistent operational state — never stores mail content."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class WatchState:
    history_id: str | None = None
    expiration_ms: int | None = None
    topic: str | None = None
    account_email: str | None = None


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> WatchState:
        if not self._path.exists():
            return WatchState()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return WatchState(
            history_id=data.get("history_id"),
            expiration_ms=data.get("expiration_ms"),
            topic=data.get("topic"),
            account_email=data.get("account_email"),
        )

    def save(self, state: WatchState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: v for k, v in asdict(state).items() if v is not None}
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def update_history_id(self, history_id: str) -> None:
        state = self.load()
        state.history_id = history_id
        self.save(state)
