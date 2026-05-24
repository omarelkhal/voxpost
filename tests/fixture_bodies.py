"""Shared email bodies from shipped speech-check JSON fixtures."""

from voxpost.speech_check.loader import load_fixture_by_id

FORWARDED_FR_PHONE = load_fixture_by_id("fr_forward_phone").event.body
