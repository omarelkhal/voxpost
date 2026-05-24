"""HF Inference API prompt check — cloud oracle for speech-check prompts only.

Not used in the listen pipeline (on-device summarization is a product requirement).
Requires HF_TOKEN or `huggingface-cli login`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voxpost.events import NewMailEvent
from voxpost.summarize import (
    _chat_system_prompt,
    _clean_chat_briefing,
    _is_qwen35,
    _normalize_body,
    build_model_input,
    format_chat_user_message,
    resolved_chat_input_format,
)

DEFAULT_HF_PROMPT_MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"


@dataclass(frozen=True)
class HfPromptJob:
    model: str
    config_dir: str | None
    input_format: str  # plain | structured


def _is_small_qwen35(model_id: str) -> bool:
    """On-device-sized Qwen3.5 — same token budget as local chat-LM path."""
    normalized = model_id.lower().replace("\\", "/")
    if not _is_qwen35(normalized):
        return False
    return any(tag in normalized for tag in ("0.8b", "0.6b", "1.7b", "1.5b", "2b"))


def _max_tokens_for_body(body_words: int, *, model: str) -> int:
    """One-shot HF budget — no retries (oracle runs must stay cheap)."""
    if _is_small_qwen35(model):
        if body_words <= 50:
            return 96
        if body_words <= 120:
            return 128
        return 160
    if body_words <= 50:
        return 128
    if body_words <= 120:
        return 192
    return 256


def _message_content(message: Any) -> str:
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    return str(content).strip() if content else ""


def _hf_message_text(message: Any, *, finish_reason: str | None = None) -> str:
    """Prefer final assistant content; avoid incomplete reasoning traces."""
    content = _message_content(message)
    if content:
        return content
    if finish_reason == "length":
        return ""

    reasoning = getattr(message, "reasoning", None)
    if reasoning is None and isinstance(message, dict):
        reasoning = message.get("reasoning")
    if not reasoning:
        return ""

    text = str(reasoning)
    for marker in (
        "*Final Decision:*",
        "*Final answer:*",
        "Final Decision:",
        "Final answer:",
        "Final Polish:",
        "Revised Draft:",
    ):
        if marker in text:
            tail = text.split(marker)[-1].strip()
            for line in reversed(tail.splitlines()):
                line = line.strip().strip("*").strip('"').strip("'")
                if line and len(line.split()) >= 4:
                    return line
    return ""


_HF_META_PREFIX = re.compile(
    r"^(?:Revised Draft|Final Polish|Briefing|Let's go with)\s*:?\s*[*\"']?\s*",
    re.IGNORECASE,
)


def _clean_hf_line(text: str) -> str:
    line = _clean_chat_briefing(text)
    line = _HF_META_PREFIX.sub("", line).strip().strip('"').strip("'")
    return re.sub(r"\s+", " ", line).strip()


def _hf_chat_line(
    client: Any,
    *,
    messages: list[dict[str, str]],
    model: str,
    body_words: int,
) -> str:
    response = client.chat_completion(
        messages=messages,
        model=model,
        max_tokens=_max_tokens_for_body(body_words, model=model),
        temperature=0.0,
    )
    choice = response.choices[0]
    raw = _hf_message_text(choice.message, finish_reason=choice.finish_reason)
    if not raw:
        return ""
    return _clean_hf_line(raw)


def build_chat_messages(
    event: NewMailEvent,
    *,
    model: str,
    config_dir: Path | None,
    input_format: str,
) -> list[dict[str, str]]:
    body_words = len(_normalize_body(event).split())
    from voxpost.user_config import resolved_speakable_lang

    lang = resolved_speakable_lang(config_dir)
    structured = input_format == "structured"
    system = _chat_system_prompt(structured=structured, lang=lang, body_words=body_words)
    email_text = build_model_input(
        event,
        model_id=model,
        input_format=input_format if structured else "plain",
    )
    user_content = format_chat_user_message(email_text, structured=structured)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def summarize_event_hf(
    event: NewMailEvent,
    *,
    model: str,
    config_dir: Path | None = None,
    input_format: str | None = None,
    token: str | None = None,
    provider: str | None = None,
) -> str:
    """One speakable line via HF chat completions (same prompts as local chat-LM path)."""
    fmt = input_format or resolved_chat_input_format(config_dir)
    messages = build_chat_messages(
        event, model=model, config_dir=config_dir, input_format=fmt
    )
    body_words = len(_normalize_body(event).split())

    from huggingface_hub import InferenceClient

    api_token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    client = InferenceClient(token=api_token, provider=provider)
    return _hf_chat_line(
        client,
        messages=messages,
        model=model,
        body_words=body_words,
    )


def summarize_event_hf_with_meta(
    event: NewMailEvent,
    *,
    model: str,
    config_dir: Path | None = None,
    input_format: str | None = None,
    token: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    fmt = input_format or resolved_chat_input_format(config_dir)
    messages = build_chat_messages(
        event, model=model, config_dir=config_dir, input_format=fmt
    )
    body_words = len(_normalize_body(event).split())

    from huggingface_hub import InferenceClient

    api_token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    client = InferenceClient(token=api_token, provider=provider)
    raw = _hf_chat_line(
        client,
        messages=messages,
        model=model,
        body_words=body_words,
    )
    return {
        "raw": raw,
        "input_format": fmt,
        "messages": messages,
    }
