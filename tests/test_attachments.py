from voxpost.attachments import extract_attachments


def test_no_attachments_plain_text():
    payload = {
        "mimeType": "text/plain",
        "body": {"data": "dGVzdA", "size": 4},
    }
    assert extract_attachments(payload) == ()


def test_single_file_attachment():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": "dGVzdA", "size": 4}},
            {
                "mimeType": "application/pdf",
                "filename": "report.pdf",
                "body": {"attachmentId": "ANGjdJ...", "size": 48291},
            },
        ],
    }
    attachments = extract_attachments(payload)
    assert len(attachments) == 1
    assert attachments[0].filename == "report.pdf"
    assert attachments[0].mime_type == "application/pdf"
    assert attachments[0].size_bytes == 48291


def test_attachment_without_filename_uses_attachment_id():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "application/octet-stream",
                "filename": "",
                "body": {"attachmentId": "xyz", "size": 100},
            },
        ],
    }
    attachments = extract_attachments(payload)
    assert len(attachments) == 1
    assert attachments[0].filename == "attachment"
    assert attachments[0].size_bytes == 100


def test_nested_multipart_attachments():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": "a", "size": 1}},
                    {"mimeType": "text/html", "body": {"data": "b", "size": 1}},
                ],
            },
            {
                "mimeType": "image/png",
                "filename": "scan.png",
                "body": {"attachmentId": "id1", "size": 2048},
            },
        ],
    }
    attachments = extract_attachments(payload)
    assert len(attachments) == 1
    assert attachments[0].filename == "scan.png"
