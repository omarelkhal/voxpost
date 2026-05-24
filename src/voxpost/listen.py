"""Listen loop — watch, Pub/Sub, history, events."""

from __future__ import annotations

import logging
import signal
import threading
import time
from collections.abc import Callable

from voxpost.config import Settings
from voxpost.console import ListenConsole, setup_listen_logging
from voxpost.events import NewMailEvent
from voxpost.tts import Speaker, supertonic_speaker_from_user_config
from voxpost.gmail_watch import renew_watch_if_needed, start_watch, stop_watch
from voxpost.history import list_new_mail_events
from voxpost.oauth import get_gmail_service, get_profile_email, load_credentials
from voxpost.pubsub_listener import run_streaming_pull
from voxpost.state import StateStore

logger = logging.getLogger(__name__)


class ListenDaemon:
    def __init__(
        self,
        settings: Settings,
        on_event: Callable[[NewMailEvent], None] | None = None,
        *,
        summarize: bool = False,
        speak: bool = False,
        speaker: Speaker | None = None,
        console: ListenConsole | None = None,
    ) -> None:
        self._settings = settings
        self._state_store = StateStore(settings.state_path)
        self._on_event = on_event or self._default_on_event
        self._summarize = summarize
        self._speak = speak
        self._speaker = speaker
        self._console = console or ListenConsole()
        self._summarizer = None
        self._shutdown = threading.Event()
        self._seen_ids: set[str] = set()
        self._lock = threading.Lock()
        self._service = None
        self._account_email = ""
        self._last_summarize_at = 0.0
        from voxpost.user_config import load_user_config, resolved_speakable_lang

        user_cfg = load_user_config(settings.config_dir)
        sum_cfg = user_cfg.summarize
        self._idle_unload_seconds = sum_cfg.idle_unload_minutes * 60
        self._summarize_backend = sum_cfg.backend
        self._summarize_model = sum_cfg.model
        self._speech_lang = resolved_speakable_lang(settings.config_dir)
        self._tts_model = user_cfg.tts.model
        self._tts_device = user_cfg.tts.device

    @staticmethod
    def _default_on_event(event: NewMailEvent) -> None:
        print(event.to_json(), flush=True)

    def _summarizer_label(self) -> tuple[str, str]:
        if self._summarizer is not None:
            return self._summarizer._summarize_backend(), self._summarizer.model_id
        from voxpost.summarize import resolved_model_id, resolved_summarize_backend

        return (
            resolved_summarize_backend(self._settings.config_dir),
            resolved_model_id(self._settings.config_dir),
        )

    def _get_summarizer(self):
        if self._summarizer is None:
            backend, model = self._summarizer_label()
            if not self._console.json_mode:
                self._console.summarizer_loading(backend, model)
            from voxpost.summarize import EmailSummarizer

            self._summarizer = EmailSummarizer(
                config_dir=self._settings.config_dir,
                local_files_only=True,
            )
        return self._summarizer

    def _maybe_unload_summarizer(self) -> None:
        if self._idle_unload_seconds <= 0 or self._summarizer is None:
            return
        if self._last_summarize_at <= 0:
            return
        if time.monotonic() - self._last_summarize_at < self._idle_unload_seconds:
            return
        logger.info(
            "Summarizer idle for %s minutes — unloading to free RAM",
            self._idle_unload_seconds // 60,
        )
        self._console.info(
            f"Summarizer idle for {self._idle_unload_seconds // 60} min — unloading to free RAM"
        )
        self._summarizer.unload()
        self._summarizer = None

    def _idle_unload_loop(self) -> None:
        while not self._shutdown.wait(timeout=60):
            if not self._summarize or self._idle_unload_seconds <= 0:
                continue
            with self._lock:
                self._maybe_unload_summarizer()

    def _emit_event(self, event: NewMailEvent) -> None:
        if not self._summarize:
            if self._console.json_mode:
                self._console.emit_json(event.to_json())
            elif self._on_event is self._default_on_event:
                self._console.raw_mail(event)
            else:
                self._on_event(event)
            return

        if not self._console.json_mode:
            self._console.mail_header(event)

        backend, model = self._summarizer_label()
        if not self._console.json_mode:
            self._console.summarizing(backend, model)

        with self._lock:
            self._maybe_unload_summarizer()
            summarized = self._get_summarizer().summarize_event(event)
            self._last_summarize_at = time.monotonic()

        self._console.emit_json(summarized.to_json())
        if not self._console.json_mode:
            self._console.speakable(summarized.speakable_line)

        if self._speak:
            self._speak_line(summarized.speakable_line)

    def _get_speaker(self) -> Speaker:
        if self._speaker is None:
            self._speaker = supertonic_speaker_from_user_config(self._settings.config_dir)
        return self._speaker

    def _warmup_tts(self) -> None:
        try:
            if not self._console.json_mode:
                self._console.info("Loading Supertonic TTS model…")
            speaker = self._get_speaker()
            warmup = getattr(speaker, "warmup", None)
            if callable(warmup):
                warmup()
            if not self._console.json_mode:
                self._console.success("TTS ready")
        except Exception:
            logger.exception("TTS warmup failed (first speak may be slower)")
            self._console.warn("TTS warmup failed — first spoken line may be slower")

    def _speak_line(self, line: str) -> None:
        try:
            from voxpost.tts import speak_from_user_config

            if not self._console.json_mode:
                self._console.speaking()
            speak_from_user_config(
                line,
                speaker=self._get_speaker(),
                config_dir=self._settings.config_dir,
            )
            if not self._console.json_mode:
                self._console.spoke()
        except Exception:
            logger.exception("TTS failed (continuing listen)")
            self._console.error("TTS playback failed — continuing to listen for mail")

    def _get_service(self):
        if self._service is None:
            creds = load_credentials(
                self._settings.token_path, self._settings.oauth_client_secrets
            )
            if creds is None:
                raise RuntimeError(
                    "Not connected. Run `voxpost connect` first."
                )
            self._service = get_gmail_service(creds)
            self._account_email = get_profile_email(self._service)
        return self._service

    def _process_notification(self, _email: str, notification_history_id: str) -> None:
        """Handle one Pub/Sub push — delay, fetch history, emit events."""
        if not self._console.json_mode:
            self._console.gmail_notification(notification_history_id)

        time.sleep(self._settings.fetch_delay_seconds)

        with self._lock:
            service = self._get_service()
            state = self._state_store.load()
            start_id = state.history_id

            if not start_id:
                start_id = notification_history_id

            events, latest = list_new_mail_events(
                service,
                self._account_email,
                start_id,
                self._seen_ids,
            )
            cursor = latest or notification_history_id

        if not self._console.json_mode:
            self._console.history_fetch(len(events))

        for event in events:
            self._emit_event(event)

        if cursor:
            with self._lock:
                self._state_store.update_history_id(cursor)

    def _renew_loop(self) -> None:
        while not self._shutdown.wait(timeout=3600):
            try:
                with self._lock:
                    service = self._get_service()
                    renew_watch_if_needed(
                        service, self._settings.topic_path, self._state_store
                    )
            except Exception:
                logger.exception("Watch renewal failed")
                self._console.warn("Gmail watch renewal failed — will retry in an hour")

    def run(self) -> None:
        service = self._get_service()
        start_watch(
            service,
            self._settings.topic_path,
            self._state_store,
            self._account_email,
        )

        if not self._console.json_mode:
            self._console.startup_ready(
                account=self._account_email,
                project=self._settings.gcp_project,
                subscription=self._settings.subscription_path,
                summarize=self._summarize,
                speak=self._speak,
                summarize_backend=self._summarize_backend,
                summarize_model=self._summarize_model,
                speech_lang=self._speech_lang if self._summarize else None,
                tts_model=self._tts_model if self._speak else None,
                tts_device=self._tts_device if self._speak else None,
            )
            self._console.waiting()

        renew_thread = threading.Thread(target=self._renew_loop, daemon=True)
        renew_thread.start()

        if self._summarize and self._idle_unload_seconds > 0:
            idle_thread = threading.Thread(target=self._idle_unload_loop, daemon=True)
            idle_thread.start()

        if self._speak:
            threading.Thread(target=self._warmup_tts, daemon=True).start()

        def handle_signal(_signum, _frame) -> None:
            self._shutdown.set()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        try:
            run_streaming_pull(
                self._settings,
                self._process_notification,
                self._shutdown,
            )
        finally:
            self._shutdown.set()
            if not self._console.json_mode:
                self._console.shutdown()
            with self._lock:
                if self._service:
                    stop_watch(self._service, self._state_store)


def run_listen(
    settings: Settings,
    *,
    summarize: bool = False,
    speak: bool = False,
    speaker: Speaker | None = None,
    json_mode: bool = False,
    verbose: bool = False,
) -> None:
    if speak and not summarize:
        summarize = True
    console = ListenConsole(json_mode=json_mode)
    setup_listen_logging(console, verbose=verbose)
    ListenDaemon(
        settings,
        summarize=summarize,
        speak=speak,
        speaker=speaker,
        console=console,
    ).run()
