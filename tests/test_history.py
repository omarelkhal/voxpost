"""Tests for history helpers."""

from voxpost.history import _labels_allow_inbox


def test_labels_allow_inbox_true():
    assert _labels_allow_inbox(["INBOX", "UNREAD"]) is True


def test_labels_allow_inbox_spam():
    assert _labels_allow_inbox(["SPAM"]) is False


def test_labels_allow_inbox_trash():
    assert _labels_allow_inbox(["TRASH"]) is False


def test_labels_allow_inbox_missing():
    assert _labels_allow_inbox(None) is None
    assert _labels_allow_inbox([]) is None


def test_labels_allow_inbox_not_inbox():
    assert _labels_allow_inbox(["SENT"]) is False
