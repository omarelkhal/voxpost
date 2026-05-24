"""Local Ollama HTTP client for Block 3 chat summarization."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT_S = 180.0


def normalize_ollama_host(host: str) -> str:
    value = (host or DEFAULT_OLLAMA_HOST).strip()
    if not value:
        value = DEFAULT_OLLAMA_HOST
    return value.rstrip("/")


def _post_json(
    host: str,
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    url = f"{normalize_ollama_host(host)}{path}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as err:
        raise RuntimeError(
            f"Cannot reach Ollama at {normalize_ollama_host(host)!r}. "
            "Is the daemon running? Try: ollama serve"
        ) from err
    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        raise RuntimeError(f"Invalid JSON from Ollama at {url}") from err


def _get_json(
    host: str,
    path: str,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    url = f"{normalize_ollama_host(host)}{path}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as err:
        raise RuntimeError(
            f"Cannot reach Ollama at {normalize_ollama_host(host)!r}. "
            "Is the daemon running? Try: ollama serve"
        ) from err
    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        raise RuntimeError(f"Invalid JSON from Ollama at {url}") from err


def list_ollama_models(host: str) -> list[str]:
    data = _get_json(host, "/api/tags")
    models = data.get("models") or []
    names: list[str] = []
    for entry in models:
        if isinstance(entry, dict):
            name = entry.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


def ollama_model_available(host: str, model: str) -> bool:
    target = model.strip()
    if not target:
        return False
    names = list_ollama_models(host)
    if target in names:
        return True
    # Accept bare name when tags include :latest suffix.
    return any(name == target or name.split(":")[0] == target.split(":")[0] for name in names)


def ollama_chat(
    *,
    host: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    think: bool = False,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> str:
    """Run one non-streaming chat completion against a local Ollama model."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": max(8, int(max_tokens)),
            "temperature": 0,
        },
    }
    if not think:
        payload["think"] = False
    data = _post_json(host, "/api/chat", payload, timeout=timeout)
    message = data.get("message")
    if not isinstance(message, dict):
        raise RuntimeError(f"Ollama chat response missing message: {data!r}")
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"Ollama chat response missing content: {data!r}")
    return content.strip()


def ollama_pull(host: str, model: str, *, timeout: float = 600.0) -> None:
    """Pull a model via Ollama's streaming pull API."""
    url = f"{normalize_ollama_host(host)}/api/pull"
    body = json.dumps({"name": model, "stream": True}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            while True:
                line = response.readline()
                if not line:
                    break
                try:
                    event = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                status = event.get("status")
                if isinstance(status, str):
                    logger.info("ollama pull: %s", status)
                if event.get("error"):
                    raise RuntimeError(str(event["error"]))
    except urllib.error.URLError as err:
        raise RuntimeError(
            f"Cannot reach Ollama at {normalize_ollama_host(host)!r}. "
            "Is the daemon running? Try: ollama serve"
        ) from err

    if not ollama_model_available(host, model):
        raise RuntimeError(f"Ollama pull finished but model {model!r} is not listed")
