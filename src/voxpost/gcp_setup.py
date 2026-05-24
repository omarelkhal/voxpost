"""Provision Gmail Pub/Sub resources via the gcloud CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

GMAIL_PUSH_SA = "serviceAccount:gmail-api-push@system.gserviceaccount.com"
DEFAULT_TOPIC = "voxpost-gmail"
DEFAULT_SUBSCRIPTION = "voxpost-gmail-pull"


class GcloudError(RuntimeError):
    pass


def _gcloud(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    if not shutil.which("gcloud"):
        raise GcloudError(
            "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
        )
    cmd = ["gcloud", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise GcloudError(
            f"gcloud failed: {' '.join(cmd)}\n{result.stderr.strip() or result.stdout}"
        )
    return result


def get_gcloud_project(explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    result = _gcloud("config", "get-value", "project", check=False)
    project = (result.stdout or "").strip()
    if not project or project == "(unset)":
        raise GcloudError(
            "No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
        )
    return project


def enable_apis(project: str) -> None:
    _gcloud(
        "services", "enable",
        "gmail.googleapis.com",
        "pubsub.googleapis.com",
        f"--project={project}",
    )


def _resource_exists(kind: str, name: str, project: str) -> bool:
    result = _gcloud(
        "pubsub", kind, "describe", name,
        f"--project={project}",
        check=False,
    )
    return result.returncode == 0


def ensure_pubsub(project: str, topic: str, subscription: str) -> None:
    if not _resource_exists("topics", topic, project):
        _gcloud("pubsub", "topics", "create", topic, f"--project={project}")
    else:
        print(f"Topic {topic} already exists")

    if not _resource_exists("subscriptions", subscription, project):
        _gcloud(
            "pubsub", "subscriptions", "create", subscription,
            f"--topic={topic}",
            f"--project={project}",
        )
    else:
        print(f"Subscription {subscription} already exists")

    _gcloud(
        "pubsub", "topics", "add-iam-policy-binding", topic,
        f"--project={project}",
        f"--member={GMAIL_PUSH_SA}",
        "--role=roles/pubsub.publisher",
    )


def grant_subscriber_to_current_user(project: str, subscription: str) -> str:
    """Grant Pub/Sub subscriber to the active gcloud account (for ADC)."""
    account = _gcloud("config", "get-value", "account").stdout.strip()
    if not account:
        raise GcloudError("No gcloud account. Run: gcloud auth login")

    _gcloud(
        "pubsub", "subscriptions", "add-iam-policy-binding", subscription,
        f"--project={project}",
        f"--member=user:{account}",
        "--role=roles/pubsub.subscriber",
    )
    return account


def save_gcp_config(
    config_dir: Path,
    project: str,
    topic: str,
    subscription: str,
) -> Path:
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "gcp.json"
    path.write_text(
        json.dumps(
            {
                "gcp_project": project,
                "pubsub_topic": topic,
                "pubsub_subscription": subscription,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def run_setup(
    config_dir: Path,
    project: str | None = None,
    topic: str = DEFAULT_TOPIC,
    subscription: str = DEFAULT_SUBSCRIPTION,
) -> dict[str, str]:
    """
    Enable APIs, create Pub/Sub resources, grant IAM, write gcp.json.

    Returns summary dict for CLI output.
    """
    resolved_project = get_gcloud_project(project)
    print(f"Using project: {resolved_project}")

    enable_apis(resolved_project)
    ensure_pubsub(resolved_project, topic, subscription)
    account = grant_subscriber_to_current_user(resolved_project, subscription)

    config_path = save_gcp_config(config_dir, resolved_project, topic, subscription)

    return {
        "project": resolved_project,
        "topic": topic,
        "subscription": subscription,
        "account": account,
        "config_path": str(config_path),
    }
