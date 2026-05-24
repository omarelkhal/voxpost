import base64

from voxpost.message_body import cap_body_text, extract_plain_text_body


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_extract_plain_text_simple():
    payload = {"mimeType": "text/plain", "body": {"data": _b64("Hello world")}}
    assert extract_plain_text_body(payload) == "Hello world"


def test_extract_plain_text_nested():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<p>no</p>")}},
            {"mimeType": "text/plain", "body": {"data": _b64("yes plain")}},
        ],
    }
    assert extract_plain_text_body(payload) == "yes plain"


def test_cap_body_text():
    text, truncated = cap_body_text("short", max_bytes=100)
    assert text == "short"
    assert truncated is False

    long_text = "a" * 50
    text, truncated = cap_body_text(long_text, max_bytes=10)
    assert len(text.encode("utf-8")) <= 10
    assert truncated is True
