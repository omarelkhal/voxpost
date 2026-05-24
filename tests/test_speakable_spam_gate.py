"""Tests for spam-template rewriting into unseen-mail briefing voice."""

from voxpost.events import NewMailEvent
from voxpost.speakable_gate import adjust_misapplied_spam_template

_HEDGE = "Worth checking — it might be spam."


def _event(**kwargs) -> NewMailEvent:
    defaults = {
        "account_id": "acct1",
        "message_id": "m1",
        "thread_id": "t1",
        "history_id": "h1",
        "from_address": "sender@example.com",
        "subject": "Subject",
        "body": "Body text here.",
        "received_at": "2026-01-01T12:00:00Z",
    }
    defaults.update(kwargs)
    return NewMailEvent(**defaults)


def test_newsletter_spam_hedged_not_asserted():
    event = _event(
        from_address="Deals Weekly <deals@shop.example>",
        subject="Don't miss our biggest sale — 50% off everything",
        body="Shop now. Unsubscribe here.",
    )
    line = "This looks like spam about a sale with fifty percent off everything."
    out = adjust_misapplied_spam_template(line, event)
    assert out.startswith("You received an email about")
    assert "fifty percent off" in out.lower()
    assert out.endswith(_HEDGE)
    assert "this looks like spam" not in out.lower()


def test_hedges_spam_on_invoice_mail():
    event = _event(
        subject="Invoice #8842 due Friday",
        body="Please pay invoice 8842 by Friday.",
    )
    line = "This looks like spam about an invoice due Friday."
    out = adjust_misapplied_spam_template(line, event)
    assert out.startswith("You received an email about")
    assert "invoice due friday" in out.lower()
    assert out.endswith(_HEDGE)


def test_hedges_spam_on_forwarded_personal_mail():
    event = _event(
        subject="Fwd: phone number",
        body="---------- Forwarded message ---------\nFrom: Marie\nCan you send your phone number?",
    )
    line = "This looks like spam about a phone number request."
    out = adjust_misapplied_spam_template(line, event)
    assert out.startswith("You received an email about")
    assert "phone number" in out.lower()
    assert out.endswith(_HEDGE)


def test_rewrites_legacy_hedge_format():
    event = _event(
        subject="Software engineering gig",
        body="We pay ninety dollars per hour for a project with our AI lab.",
    )
    line = (
        "It's about a ninety dollar per hour software engineering project with an AI lab. "
        "Worth checking if you're not sure. Maybe it's spam."
    )
    out = adjust_misapplied_spam_template(line, event)
    assert out.startswith("You received an email about a ninety dollar")
    assert out.endswith(_HEDGE)
    assert "It's about" not in out


def test_rewrites_firm_spam_on_briefing_line():
    event = _event(subject="Sale")
    line = (
        "You received an email about a fifty percent off weekend sale. "
        "This looks like spam."
    )
    out = adjust_misapplied_spam_template(line, event)
    assert out.endswith(_HEDGE)
    assert "this looks like spam" not in out.lower()


def test_already_hedged_briefing_unchanged():
    event = _event(subject="Sale")
    line = (
        "You received an email about a fifty percent off weekend sale. "
        "Worth checking — it might be spam."
    )
    assert adjust_misapplied_spam_template(line, event) == line


def test_non_spam_line_unchanged():
    event = _event(subject="Deploy failed")
    line = "Staging deploy failed on the migration pipeline."
    assert adjust_misapplied_spam_template(line, event) == line
