"""Runtime configuration from environment, gcp.json, and gcloud defaults."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def _default_config_dir() -> Path:
    explicit = os.environ.get("VOXPOST_CONFIG_DIR") or os.environ.get("MAILCUE_CONFIG_DIR")
    if explicit:
        return _expand(explicit)
    voxpost_dir = _expand("~/.config/voxpost")
    legacy_dir = _expand("~/.config/mailcue")
    if voxpost_dir.exists() or not legacy_dir.exists():
        return voxpost_dir
    return legacy_dir


def _env(name: str) -> str | None:
    """Read VOXPOST_* with legacy MAILCUE_* fallback."""
    return os.environ.get(name) or os.environ.get(name.replace("VOXPOST_", "MAILCUE_", 1))


def _gcloud_project() -> str | None:
    if not shutil.which("gcloud"):
        return None
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        project = (result.stdout or "").strip()
        if project and project != "(unset)":
            return project
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def _load_gcp_json(config_dir: Path) -> dict[str, str]:
    path = config_dir / "gcp.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Settings:
    gcp_project: str
    pubsub_topic: str
    pubsub_subscription: str
    oauth_client_secrets: Path
    pubsub_credentials: Path | None
    config_dir: Path
    fetch_delay_seconds: float

    @property
    def topic_path(self) -> str:
        return f"projects/{self.gcp_project}/topics/{self.pubsub_topic}"

    @property
    def subscription_path(self) -> str:
        return f"projects/{self.gcp_project}/subscriptions/{self.pubsub_subscription}"

    @property
    def token_path(self) -> Path:
        return self.config_dir / "token.json"

    @property
    def state_path(self) -> Path:
        return self.config_dir / "state.json"


def _resolve_oauth_secrets(config_dir: Path) -> Path | None:
    oauth_env = _env("VOXPOST_OAUTH_CLIENT_SECRETS")
    if oauth_env:
        return _expand(oauth_env)
    for candidate in (
        config_dir / "client_secret.json",
        config_dir / "credentials.json",
        Path.cwd() / "client_secret.json",
    ):
        if candidate.exists():
            return candidate.resolve()
    return None


def load_settings() -> Settings:
    """
    Load settings with precedence: env vars → ~/.config/voxpost/gcp.json → gcloud defaults.

    Pub/Sub auth: optional VOXPOST_PUBSUB_CREDENTIALS JSON file; otherwise uses
    Application Default Credentials (run `gcloud auth application-default login`).
    """
    config_dir = _default_config_dir()
    gcp_file = _load_gcp_json(config_dir)

    gcp_project = (
        _env("VOXPOST_GCP_PROJECT")
        or gcp_file.get("gcp_project")
        or _gcloud_project()
    )
    pubsub_topic = (
        _env("VOXPOST_PUBSUB_TOPIC")
        or gcp_file.get("pubsub_topic")
        or "voxpost-gmail"
    )
    pubsub_subscription = (
        _env("VOXPOST_PUBSUB_SUBSCRIPTION")
        or gcp_file.get("pubsub_subscription")
        or "voxpost-gmail-pull"
    )

    oauth_secrets = _resolve_oauth_secrets(config_dir)
    pubsub_creds_env = _env("VOXPOST_PUBSUB_CREDENTIALS")
    pubsub_credentials = _expand(pubsub_creds_env) if pubsub_creds_env else None

    delay = float(_env("VOXPOST_FETCH_DELAY_SECONDS") or "2")

    missing: list[str] = []
    if not gcp_project:
        missing.append(
            "GCP project (run `voxpost setup-gcp` or set VOXPOST_GCP_PROJECT / gcloud config)"
        )
    if oauth_secrets is None:
        missing.append(
            "OAuth client secrets (download Desktop OAuth JSON to "
            f"{config_dir}/client_secret.json or set VOXPOST_OAUTH_CLIENT_SECRETS)"
        )

    if missing:
        raise ValueError(
            "Missing configuration:\n  - "
            + "\n  - ".join(missing)
            + "\nSee docs/SETUP.md"
        )

    return Settings(
        gcp_project=gcp_project,
        pubsub_topic=pubsub_topic,
        pubsub_subscription=pubsub_subscription,
        oauth_client_secrets=oauth_secrets,
        pubsub_credentials=pubsub_credentials,
        config_dir=config_dir,
        fetch_delay_seconds=delay,
    )
