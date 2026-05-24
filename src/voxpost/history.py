"""Resolve Pub/Sub notifications into NewMailEvent via history.list."""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.errors import HttpError

from voxpost.attachments import extract_attachments
from voxpost.events import NewMailEvent
from voxpost.message_body import cap_body_text, extract_plain_text_body

logger = logging.getLogger(__name__)

HISTORY_TYPES = ["messageAdded"]
SPAM_TRASH = {"SPAM", "TRASH"}
MAX_BODY_BYTES = 20_000


def _header_map(payload_headers: list[dict[str, str]]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in payload_headers}


def _labels_allow_inbox(label_ids: list[str] | None) -> bool | None:
    """
    Return True/False if label_ids are enough to decide inbox eligibility.
    Return None if label_ids are missing and a messages.get is required.
    """
    if not label_ids:
        return None
    labels = set(label_ids)
    if labels & SPAM_TRASH:
        return False
    return "INBOX" in labels


def _fetch_message(service, message_id: str) -> dict[str, Any] | None:
    """
    Fetch full message (headers + body). Returns None on 404.
    Body is only kept in memory for the event — never written to disk.
    """
    try:
        return (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except HttpError as err:
        if err.resp.status == 404:
            logger.info(
                "Skipping message %s — not found (deleted or not indexed yet)",
                message_id,
            )
            return None
        raise


def list_new_mail_events(
    service,
    account_id: str,
    start_history_id: str,
    seen_message_ids: set[str],
) -> tuple[list[NewMailEvent], str | None]:
    """
    Fetch history since start_history_id.

    Returns (events, latest_history_id). latest_history_id is used to advance the cursor.
    """
    events: list[NewMailEvent] = []
    latest_history_id: str | None = None
    page_token: str | None = None

    while True:
        try:
            response = (
                service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=HISTORY_TYPES,
                    pageToken=page_token,
                )
                .execute()
            )
        except HttpError as err:
            if err.resp.status == 404:
                logger.warning(
                    "historyId stale (%s); resetting cursor from profile",
                    start_history_id,
                )
                profile = service.users().getProfile(userId="me").execute()
                return [], str(profile["historyId"])
            raise

        for record in response.get("history", []):
            record_history_id = str(record.get("id", ""))
            if record_history_id:
                latest_history_id = record_history_id

            for added in record.get("messagesAdded", []):
                message = added.get("message", {})
                message_id = message.get("id")
                thread_id = message.get("threadId", "")
                if not message_id or message_id in seen_message_ids:
                    continue

                inbox_decision = _labels_allow_inbox(message.get("labelIds"))
                if inbox_decision is False:
                    seen_message_ids.add(message_id)
                    continue

                msg = _fetch_message(service, message_id)
                if msg is None:
                    seen_message_ids.add(message_id)
                    continue

                if inbox_decision is None:
                    labels = set(msg.get("labelIds", []))
                    if labels & SPAM_TRASH or "INBOX" not in labels:
                        seen_message_ids.add(message_id)
                        continue

                payload = msg.get("payload") or {}
                headers = _header_map(payload.get("headers", []))
                raw_body = extract_plain_text_body(payload)
                body, body_truncated = cap_body_text(raw_body, MAX_BODY_BYTES)
                attachments = extract_attachments(payload)
                seen_message_ids.add(message_id)

                events.append(
                    NewMailEvent(
                        account_id=account_id,
                        message_id=message_id,
                        thread_id=thread_id or msg.get("threadId", ""),
                        history_id=record_history_id or start_history_id,
                        received_at=headers.get("date"),
                        from_address=headers.get("from"),
                        subject=headers.get("subject"),
                        body=body or None,
                        body_truncated=body_truncated,
                        has_attachments=len(attachments) > 0,
                        attachment_count=len(attachments),
                        attachments=attachments,
                    )
                )

        page_token = response.get("nextPageToken")
        if not page_token:
            history_id = response.get("historyId")
            if history_id:
                latest_history_id = str(history_id)
            break

    return events, latest_history_id


def decode_pubsub_data(data: bytes) -> dict[str, Any]:
    """Parse Gmail push notification JSON from Pub/Sub message data."""
    import json

    return json.loads(data.decode("utf-8"))
