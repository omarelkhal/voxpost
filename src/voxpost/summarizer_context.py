"""Structured email facts for chat-LM summarizer input."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from voxpost.email_clean import body_has_forward_block, extract_forwarded_sender
from voxpost.email_entities import extract_email_entities
from voxpost.events import NewMailEvent
from voxpost.speakable_fallback import display_name
from voxpost.speakable_polish import polish_email_text


def _is_forward_subject(subject: str | None) -> bool:
    if not subject:
        return False
    head = subject.strip().lower()
    return head.startswith(("fwd:", "fw:", "tr:", "transféré:", "transfere:"))


def _raw_body_has_forward_marker(raw_body: str) -> bool:
    return body_has_forward_block(raw_body)


def detect_is_forward(event: NewMailEvent, *, raw_body: str | None = None) -> bool:
    """True when the message is a forward (subject or body markers)."""
    raw = raw_body if raw_body is not None else (event.body or "")
    if _is_forward_subject(event.subject):
        return True
    if _raw_body_has_forward_marker(raw):
        return True
    if extract_forwarded_sender(raw):
        return True
    return False


def _polish_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    text = polish_email_text(subject.strip())
    return text or None


@dataclass(frozen=True)
class SummarizerEmailContext:
    """
    Canonical facts passed to instruction-tuned chat models.

    JSON keys (stable — document in docs/BLOCK_3_SUMMARIZE.md):
      account          — recipient mailbox (connected Gmail)
      envelope_from    — Gmail From header (forwarder on forwards)
      original_sender  — who wrote the message (inner sender when forwarded)
      is_forward       — whether envelope_from is not the author
      subject          — cleaned subject line
      body             — cleaned inner body (no forward wrappers)
      body_truncated   — true if body was clipped for token budget
      has_attachments  — metadata only; no attachment bytes
      attachments      — list of {filename, mime_type}
      signatory_name   — closing signature (HR letter author), when detected
      signatory_title  — job title on sign-off line, when detected
      company          — employer/org mentioned in body, when detected
      application_role — role from subject (e.g. job title), when detected
    """

    account: str | None
    envelope_from: str | None
    original_sender: str | None
    is_forward: bool
    subject: str | None
    body: str
    body_truncated: bool
    has_attachments: bool
    attachments: tuple[dict[str, str], ...]
    signatory_name: str | None = None
    signatory_title: str | None = None
    company: str | None = None
    application_role: str | None = None

    def to_json(self) -> str:
        payload = {
            "account": self.account,
            "envelope_from": self.envelope_from,
            "original_sender": self.original_sender,
            "is_forward": self.is_forward,
            "subject": self.subject,
            "body": self.body,
            "body_truncated": self.body_truncated,
            "has_attachments": self.has_attachments,
            "attachments": list(self.attachments),
            "signatory_name": self.signatory_name,
            "signatory_title": self.signatory_title,
            "company": self.company,
            "application_role": self.application_role,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_summarizer_context(
    event: NewMailEvent,
    *,
    normalized_body: str,
    body_truncated: bool = False,
) -> SummarizerEmailContext:
    """Build structured context from a mail event and pre-cleaned body text."""
    raw_body = event.body or ""
    envelope = polish_email_text((event.from_address or "").strip()) or None
    subject = _polish_subject(event.subject)
    is_forward = detect_is_forward(event, raw_body=raw_body)

    entities = extract_email_entities(
        normalized_body,
        subject=event.subject,
    )
    inner_name = extract_forwarded_sender(raw_body)
    if entities.signatory_name:
        original = entities.signatory_name
    elif inner_name:
        original = inner_name
    else:
        original = display_name(event.from_address)

    attachments = tuple(
        {"filename": a.filename, "mime_type": a.mime_type}
        for a in event.attachments
    )

    return SummarizerEmailContext(
        account=event.account_id or None,
        envelope_from=envelope,
        original_sender=original or None,
        is_forward=is_forward,
        subject=subject,
        body=normalized_body if normalized_body else "(empty body)",
        body_truncated=body_truncated,
        has_attachments=event.has_attachments,
        attachments=attachments,
        signatory_name=entities.signatory_name,
        signatory_title=entities.signatory_title,
        company=entities.company,
        application_role=entities.application_role,
    )


def body_was_truncated(event: NewMailEvent, normalized_body: str, *, max_chars: int) -> bool:
    """True when normalization clipped the cleaned body."""
    from voxpost.email_clean import clean_email_body

    raw = clean_email_body(event.body or "")
    raw = polish_email_text(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return len(raw) > max_chars
