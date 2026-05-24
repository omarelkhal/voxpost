import json

from voxpost.attachments import AttachmentInfo
from voxpost.events import NewMailEvent


def test_new_mail_event_to_json():
    event = NewMailEvent(
        account_id="me@example.com",
        message_id="abc123",
        thread_id="thread1",
        history_id="999",
        received_at="Thu, 1 Jan 2026 12:00:00 +0000",
        from_address="sender@example.com",
        subject="Hello",
    )
    data = json.loads(event.to_json())
    assert data["message_id"] == "abc123"
    assert data["from_address"] == "sender@example.com"
    assert data["has_attachments"] is False
    assert data["attachment_count"] == 0
    assert data["attachments"] == []


def test_new_mail_event_attachments_in_json():
    event = NewMailEvent(
        account_id="me@example.com",
        message_id="abc123",
        thread_id="thread1",
        history_id="999",
        has_attachments=True,
        attachment_count=1,
        attachments=(
            AttachmentInfo(
                filename="report.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
            ),
        ),
    )
    data = json.loads(event.to_json())
    assert data["has_attachments"] is True
    assert data["attachment_count"] == 1
    assert data["attachments"] == [
        {
            "filename": "report.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
        }
    ]
