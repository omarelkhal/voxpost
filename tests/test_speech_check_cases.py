"""Speech-check fixture set — breadth and uniqueness."""

from voxpost.speech_check_cases import speech_check_cases


def test_speech_check_has_extended_fixture_count():
    cases = speech_check_cases()
    assert len(cases) >= 21


def test_speech_check_case_ids_unique():
    cases = speech_check_cases()
    ids = [c.case_id for c in cases]
    assert len(ids) == len(set(ids))


def test_core_and_extended_ids_present():
    ids = {c.case_id for c in speech_check_cases()}
    assert "fr_forward_phone" in ids
    assert "de_tax_notice" in ids
    assert "en_angry_order" in ids
    assert "en_subject_only_flight" in ids
