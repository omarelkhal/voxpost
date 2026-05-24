import json
from pathlib import Path

from voxpost.state import StateStore, WatchState


def test_state_store_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.save(
        WatchState(
            history_id="12345",
            expiration_ms=1730000000000,
            topic="projects/p/topics/t",
            account_email="u@gmail.com",
        )
    )
    loaded = store.load()
    assert loaded.history_id == "12345"
    assert loaded.account_email == "u@gmail.com"


def test_state_update_history_id(tmp_path: Path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.save(WatchState(history_id="100"))
    store.update_history_id("200")
    assert store.load().history_id == "200"
    # No mail content in file
    raw = json.loads(path.read_text())
    assert "subject" not in raw
    assert "body" not in raw
