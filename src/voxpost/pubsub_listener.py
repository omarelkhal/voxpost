"""Pub/Sub streaming pull subscriber for Gmail push notifications."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

import google.auth
from google.cloud import pubsub_v1
from google.oauth2 import service_account

from voxpost.config import Settings

logger = logging.getLogger(__name__)


def build_subscriber(settings: Settings) -> pubsub_v1.SubscriberClient:
    if settings.pubsub_credentials is not None:
        credentials = service_account.Credentials.from_service_account_file(
            str(settings.pubsub_credentials)
        )
        return pubsub_v1.SubscriberClient(credentials=credentials)

    credentials, project = google.auth.default()
    logger.info(
        "Pub/Sub using Application Default Credentials (project=%s). "
        "If auth fails, run: gcloud auth application-default login",
        project or settings.gcp_project,
    )
    return pubsub_v1.SubscriberClient(credentials=credentials)


def run_streaming_pull(
    settings: Settings,
    on_notification: Callable[[str, str], None],
    shutdown_event: threading.Event,
) -> None:
    """
    Block until shutdown_event is set.

    on_notification(email_address, history_id) is called for each Pub/Sub message.
    """
    subscriber = build_subscriber(settings)
    subscription = settings.subscription_path

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        if shutdown_event.is_set():
            message.nack()
            return
        try:
            import json

            payload = json.loads(message.data.decode("utf-8"))
            email = payload.get("emailAddress", "")
            history_id = str(payload.get("historyId", ""))
            if email and history_id:
                on_notification(email, history_id)
            message.ack()
        except Exception:
            logger.exception("Failed to process Pub/Sub message")
            message.nack()

    streaming_future = subscriber.subscribe(subscription, callback=callback)
    logger.info("Pub/Sub streaming pull started on %s", subscription)

    try:
        while not shutdown_event.is_set():
            time.sleep(0.5)
    finally:
        streaming_future.cancel()
        streaming_future.result(timeout=30)
        subscriber.close()
        logger.info("Pub/Sub subscriber stopped")
