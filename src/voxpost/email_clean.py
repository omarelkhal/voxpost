"""Strip forwards, signatures, and disclaimers before summarization."""

from __future__ import annotations

import re

_FORWARD_SPLIT = re.compile(
    r"(?:-{5,}\s*Forwarded message\s*-{5,}|"
    r"Begin forwarded message:|"
    r"Message transféré\s*:?\s*-{5,})",
    re.IGNORECASE,
)

_HEADER_LINE = re.compile(
    r"^(?:De|From|Date|Subject|To|Cc|Objet|À)\s*:.*\n?",
    re.IGNORECASE | re.MULTILINE,
)

_URL = re.compile(r"https?://\S+|<https?://[^>]+>")

_DISCLAIMER_START = re.compile(
    r"\bThis electronic mail transmission\b|"
    r"\bconfidential information intended only\b|"
    r"\bstrictly prohibited\b",
    re.IGNORECASE,
)

_SIGNATURE_DELIM = re.compile(r"\n--(?:\s|\n|$)")

_CONTACT_LINE = re.compile(
    r"^\*?(?:Office|Mobile|Fax|Skype|Email|Web|Tel)\*?\s*:.+$",
    re.IGNORECASE | re.MULTILINE,
)

_FORWARDED_FROM = re.compile(
    r"(?:De|From)\s*:\s*(.+?)(?:\n|<|$)",
    re.IGNORECASE,
)


def body_has_forward_block(raw_body: str) -> bool:
    """True when the raw body contains a forwarded-message delimiter."""
    if not raw_body or not raw_body.strip():
        return False
    return bool(_FORWARD_SPLIT.search(raw_body))


def extract_forwarded_sender(raw_body: str) -> str | None:
    """Best-effort inner sender from forward header block(s)."""
    matches = _FORWARDED_FROM.findall(raw_body)
    if not matches:
        return None
    # Nested forwards: last De/From block is usually the original author.
    name = matches[-1].strip().strip('"')
    if not name:
        return None
    if "<" in name:
        name = name.split("<", 1)[0].strip() or name.split("<", 1)[1].rstrip(">").strip()
    return name or None


def clean_email_body(raw: str) -> str:
    """
    Remove forward wrappers, signatures, URLs, and legal footers.

    Keeps the substantive message text the summarizer should read.
    """
    if not raw or not raw.strip():
        return ""

    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    while _FORWARD_SPLIT.search(text):
        text = _FORWARD_SPLIT.split(text, maxsplit=1)[-1]

    # Drop repeated forward header lines (De:/From:/Date:/Subject:/To:).
    for _ in range(8):
        updated = _HEADER_LINE.sub("", text, count=1)
        if updated == text:
            break
        text = updated

    sig = _SIGNATURE_DELIM.search(text)
    if sig:
        text = text[: sig.start()]

    disclaimer = _DISCLAIMER_START.search(text)
    if disclaimer:
        text = text[: disclaimer.start()]

    text = _URL.sub(" ", text)
    text = _CONTACT_LINE.sub("", text)
    text = re.sub(r"\*+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
