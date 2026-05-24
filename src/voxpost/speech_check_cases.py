"""Speech-check fixture cases (loaded from ``speech_check/fixtures/*.json``)."""

from __future__ import annotations

from voxpost.speech_check.case import SpeechCheckCase
from voxpost.speech_check.loader import list_fixture_ids, load_fixtures

__all__ = ["SpeechCheckCase", "list_speech_check_case_ids", "speech_check_cases"]


def list_speech_check_case_ids() -> tuple[str, ...]:
    """All fixture case IDs currently shipped in the repo."""
    return list_fixture_ids()


def speech_check_cases() -> tuple[SpeechCheckCase, ...]:
    """Load every speech-check email fixture (one file per case)."""
    return load_fixtures()
