"""Speech-check language helpers."""

import pytest

from voxpost.speech_check_runner import filter_speech_cases
from voxpost.speech_check_cases import list_fixture_input_langs
from voxpost.speech_langs import (
    SUPERTONIC_OUTPUT_LANGS,
    describe_input_langs,
    infer_fixture_input_lang,
    validate_output_lang,
)


def test_infer_fixture_input_lang_from_case_id():
    assert infer_fixture_input_lang("en_short_ack") == "en"
    assert infer_fixture_input_lang("fr_forward_phone") == "fr"
    assert infer_fixture_input_lang("ja_en_mixed_vendor") == "ja"


def test_infer_fixture_input_lang_explicit_override():
    assert infer_fixture_input_lang("ja_en_mixed_vendor", "ja") == "ja"


def test_validate_output_lang_supertonic():
    assert validate_output_lang("EN") == "en"
    assert validate_output_lang(" fr ") == "fr"


def test_validate_output_lang_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported output language"):
        validate_output_lang("xx")


def test_filter_speech_cases_by_input_lang():
    en_cases = filter_speech_cases(input_lang="en")
    assert len(en_cases) == 15
    assert all(c.input_lang == "en" for c in en_cases)


def test_filter_speech_cases_unknown_input_lang():
    with pytest.raises(ValueError, match="No fixtures for input language"):
        filter_speech_cases(input_lang="zh")


def test_list_fixture_input_langs():
    langs = list_fixture_input_langs()
    assert "en" in langs
    assert "fr" in langs
    assert langs == tuple(sorted(langs))


def test_describe_input_langs_multi():
    cases = filter_speech_cases()
    assert describe_input_langs(cases) == "multi"


def test_describe_input_langs_single():
    cases = filter_speech_cases(input_lang="fr")
    assert describe_input_langs(cases) == "fr"


def test_supertonic_output_lang_count():
    assert len(SUPERTONIC_OUTPUT_LANGS) == 31
