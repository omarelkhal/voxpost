import json
from pathlib import Path

import pytest

from voxpost.config import load_settings


def test_load_settings_from_gcp_json(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "voxpost"
    config_dir.mkdir()
    (config_dir / "gcp.json").write_text(
        json.dumps(
            {
                "gcp_project": "my-proj",
                "pubsub_topic": "t1",
                "pubsub_subscription": "s1",
            }
        ),
        encoding="utf-8",
    )
    (config_dir / "client_secret.json").write_text("{}", encoding="utf-8")

    monkeypatch.delenv("VOXPOST_GCP_PROJECT", raising=False)
    monkeypatch.delenv("VOXPOST_PUBSUB_TOPIC", raising=False)
    monkeypatch.delenv("VOXPOST_PUBSUB_SUBSCRIPTION", raising=False)
    monkeypatch.delenv("VOXPOST_OAUTH_CLIENT_SECRETS", raising=False)
    monkeypatch.delenv("VOXPOST_PUBSUB_CREDENTIALS", raising=False)
    monkeypatch.setenv("VOXPOST_CONFIG_DIR", str(config_dir))

    settings = load_settings()
    assert settings.gcp_project == "my-proj"
    assert settings.pubsub_topic == "t1"
    assert settings.pubsub_subscription == "s1"
    assert settings.pubsub_credentials is None


def test_load_settings_missing_oauth(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "voxpost"
    config_dir.mkdir()
    (config_dir / "gcp.json").write_text(
        json.dumps({"gcp_project": "p"}), encoding="utf-8"
    )
    monkeypatch.setenv("VOXPOST_CONFIG_DIR", str(config_dir))
    monkeypatch.delenv("VOXPOST_OAUTH_CLIENT_SECRETS", raising=False)

    with pytest.raises(ValueError, match="OAuth client secrets"):
        load_settings()
