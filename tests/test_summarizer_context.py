"""Tests for structured summarizer email context."""

import json

from voxpost.events import NewMailEvent
from voxpost.speech_check_cases import FORWARDED_FR_PHONE
from voxpost.summarizer_context import (
    build_summarizer_context,
    detect_is_forward,
)
from voxpost.summarize import build_model_input, sample_mail_event


def test_forward_fr_phone_context():
    event = NewMailEvent(
        account_id="user@gmail.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject="Fwd:",
        body=FORWARDED_FR_PHONE,
    )
    assert detect_is_forward(event) is True
    ctx = build_summarizer_context(
        event,
        normalized_body="Bonjour Omar… téléphone…",
    )
    assert ctx.is_forward is True
    assert ctx.original_sender == "Mustafa Nadir Chekroun"
    assert ctx.envelope_from is not None
    assert "Omar" in ctx.envelope_from
    payload = json.loads(ctx.to_json())
    assert payload["is_forward"] is True
    assert payload["original_sender"] == "Mustafa Nadir Chekroun"


def test_structured_model_input_is_json_for_qwen():
    event = sample_mail_event()
    text = build_model_input(
        event,
        model_id="Qwen/Qwen3.5-0.8B",
        input_format="structured",
    )
    data = json.loads(text)
    assert data["original_sender"] == "Alex Chen"
    assert data["has_attachments"] is True
    assert data["attachments"][0]["filename"] == "error.log"
    assert "staging deploy failed" in data["body"].lower()


def test_plain_model_input_includes_signatory_and_company():
    from voxpost.summarize import _email_context

    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="OMAR EL <elkhalomar0@gmail.com>",
        subject="Fwd: Update regarding your Research Associate - Data application",
        body=(
            "Hi Omar,\n\nAfter reviewing applicants, we've decided to move forward "
            "with another candidate.\n\nThank you for your interest in Mayerfeld Consulting.\n"
            "Sincerely,\n\n*Isabel Herrera*\nSenior HR Strategist\n"
        ),
    )
    from voxpost.email_clean import clean_email_body

    body = clean_email_body(event.body or "")
    text = _email_context(event, body)
    assert "Signatory: Isabel Herrera" in text
    assert "Company: Mayerfeld Consulting" in text
    assert "Role: Research Associate - Data" in text
    assert "From: OMAR EL" not in text
