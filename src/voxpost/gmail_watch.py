"""Gmail users.watch lifecycle."""

from __future__ import annotations

import logging
import time

from voxpost.state import StateStore, WatchState

logger = logging.getLogger(__name__)

INBOX_LABEL = "INBOX"
# Renew watch when less than this many ms remain (24 hours)
RENEW_BEFORE_MS = 24 * 60 * 60 * 1000


def start_watch(service, topic_path: str, state_store: StateStore, account_email: str) -> WatchState:
    """Register INBOX watch and persist historyId + expiration."""
    body = {"topicName": topic_path, "labelIds": [INBOX_LABEL]}
    response = service.users().watch(userId="me", body=body).execute()

    state = state_store.load()
    state.history_id = str(response["historyId"])
    state.expiration_ms = int(response["expiration"])
    state.topic = topic_path
    state.account_email = account_email
    state_store.save(state)

    logger.info(
        "Gmail watch started history_id=%s expiration_ms=%s",
        state.history_id,
        state.expiration_ms,
    )
    return state


def renew_watch_if_needed(service, topic_path: str, state_store: StateStore) -> None:
    """Renew watch before expiration (~7 day Gmail limit)."""
    state = state_store.load()
    if not state.expiration_ms:
        return

    now_ms = int(time.time() * 1000)
    if state.expiration_ms - now_ms > RENEW_BEFORE_MS:
        return

    logger.info("Renewing Gmail watch (expiration approaching)")
    account = state.account_email or ""
    start_watch(service, topic_path, state_store, account)


def stop_watch(service, state_store: StateStore) -> None:
    """Stop mailbox watch and clear watch metadata (keeps history_id cursor)."""
    try:
        service.users().stop(userId="me").execute()
        logger.info("Gmail watch stopped")
    except Exception as exc:  # noqa: BLE001 — best-effort on shutdown
        logger.warning("Failed to stop watch: %s", exc)

    state = state_store.load()
    state.expiration_ms = None
    state.topic = None
    state_store.save(state)
