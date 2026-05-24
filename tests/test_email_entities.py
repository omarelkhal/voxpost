"""Tests for signatory, company, and role extraction."""

from voxpost.email_clean import clean_email_body
from voxpost.email_entities import (
    extract_email_entities,
    is_application_rejection,
)
from voxpost.events import NewMailEvent
from voxpost.speakable_fallback import fallback_speakable_line, misattributes_forward
from voxpost.summarizer_context import build_summarizer_context

MAYERFELD_BODY = """Hi Omar,

Thank you for taking the time to reply to our questions and for the clarity
and structure in the way you described your analytical approach.

After reviewing the full pool of applicants, we've decided to move forward
with another candidate for this position.

Thank you again for your interest in Mayerfeld Consulting. We wish you the
best with your next steps and continued progress in your analytical work.
Sincerely,

*Isabel Herrera*
Senior HR Strategist
"""

MAYERFELD_SUBJECT = "Fwd: Update regarding your Research Associate - Data application"


def test_extract_mayerfeld_entities():
    entities = extract_email_entities(MAYERFELD_BODY, subject=MAYERFELD_SUBJECT)
    assert entities.signatory_name == "Isabel Herrera"
    assert entities.signatory_title == "Senior HR Strategist"
    assert entities.company == "Mayerfeld Consulting"
    assert entities.application_role == "Research Associate - Data"


def test_is_application_rejection():
    assert is_application_rejection(MAYERFELD_BODY) is True
    assert is_application_rejection("Thanks for your order confirmation.") is False


def test_summarizer_context_prefers_signatory_over_forwarder():
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="OMAR EL <elkhalomar0@gmail.com>",
        subject=MAYERFELD_SUBJECT,
        body=MAYERFELD_BODY,
    )
    cleaned = clean_email_body(event.body or "")
    ctx = build_summarizer_context(event, normalized_body=cleaned)
    assert ctx.original_sender == "Isabel Herrera"
    assert ctx.company == "Mayerfeld Consulting"
    assert ctx.application_role == "Research Associate - Data"


def test_misattributes_forward_rejects_omar_when_signatory_present():
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="OMAR EL <elkhalomar0@gmail.com>",
        subject=MAYERFELD_SUBJECT,
        body=MAYERFELD_BODY,
    )
    bad = "Omar wrote, and he wants to move forward with another candidate."
    assert misattributes_forward(bad, event) is True
    good = "Isabel Herrera from Mayerfeld Consulting declined your application."
    assert misattributes_forward(good, event) is False


def test_fallback_rejection_line():
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="OMAR EL <elkhalomar0@gmail.com>",
        subject=MAYERFELD_SUBJECT,
        body=MAYERFELD_BODY,
    )
    line = fallback_speakable_line(event)
    assert "Isabel Herrera" in line
    assert "Mayerfeld Consulting" in line
    assert "declined" in line.lower()
    assert "Research Associate" in line
    assert "Omar wrote" not in line
