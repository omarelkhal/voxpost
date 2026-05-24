"""Unit tests for speech check grading (no model load)."""

from voxpost.speech_check_cases import speech_check_cases
from voxpost.speech_check_runner import SpeechGrade, grade_speech_line


def test_grade_rejects_forbidden_phrase():
    case = next(c for c in speech_check_cases() if c.case_id == "fr_forward_phone")
    grade, notes = grade_speech_line(
        case,
        "Omar est un avocat à l'université de Ouagadougou.",
        used_fallback=False,
    )
    assert grade == SpeechGrade.FAIL
    assert notes


def test_grade_accepts_good_fallback_line():
    case = next(c for c in speech_check_cases() if c.case_id == "fr_forward_phone")
    line = (
        "Mustafa Nadir Chekroun says: Bonjour Omar j'espère que tu vas bien "
        "je suis un client chez vous possible d'avoir votre numéro de téléphone merci."
    )
    grade, _ = grade_speech_line(case, line, used_fallback=True)
    assert grade == SpeechGrade.WEAK
