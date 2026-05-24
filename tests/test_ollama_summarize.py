"""Tests for Ollama summarizer backend."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

import pytest

from voxpost.ollama_client import (
    list_ollama_models,
    ollama_chat,
    ollama_model_available,
)
from voxpost.summarize import EmailSummarizer, sample_mail_event


def test_ollama_chat_parses_response():
    payload = {
        "message": {"role": "assistant", "content": "Alex says the deploy failed."},
    }
    body = json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        return BytesIO(body)

    with patch("urllib.request.urlopen", fake_urlopen):
        line = ollama_chat(
            host="http://127.0.0.1:11434",
            model="qwen3.5:2b",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=48,
        )
    assert line == "Alex says the deploy failed."


def test_ollama_model_available_matches_tag():
    body = json.dumps({"models": [{"name": "qwen3.5:2b"}]}).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        if request.method == "GET":
            return BytesIO(body)
        raise AssertionError(f"unexpected method {request.method}")

    with patch("urllib.request.urlopen", fake_urlopen):
        assert ollama_model_available("http://127.0.0.1:11434", "qwen3.5:2b")
        assert list_ollama_models("http://127.0.0.1:11434") == ["qwen3.5:2b"]


def test_email_summarizer_ollama_path(tmp_path):
    cfg = tmp_path / "voxpost.toml"
    cfg.write_text(
        """
[summarize]
backend = "ollama"
model = "qwen3.5:2b"
ollama_host = "http://127.0.0.1:11434"
chat_input_format = "plain"

[speech]
mode = "fixed"
target_lang = "en"
""",
        encoding="utf-8",
    )
    summarizer = EmailSummarizer(config_dir=tmp_path, model="qwen3.5:2b")
    with patch("voxpost.ollama_client.ollama_model_available", return_value=True):
        with patch(
            "voxpost.ollama_client.ollama_chat",
            return_value="Alex Chen says the staging deploy failed.",
        ):
            line = summarizer.summarize_event_text(sample_mail_event())
    assert "deploy failed" in line.lower()
    assert summarizer._backend == "ollama"
