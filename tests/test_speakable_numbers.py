"""Tests for TTS number spelling and verification-code speakable lines."""

from voxpost.events import NewMailEvent
from voxpost.speakable_fallback import fallback_speakable_line
from voxpost.speakable_numbers import (
    extract_verification_code,
    polish_numbers_for_tts,
    spell_cardinal,
    spell_digits,
    verification_code_line,
)
from voxpost.speakable_polish import polish_for_tts


def test_spell_digits_en():
    assert spell_digits("311164", lang="en") == "three one one one six four"


def test_spell_cardinal_money_scale():
    assert spell_cardinal(1500, lang="en") == "one thousand five hundred"
    assert spell_cardinal(2_500_000, lang="en") == "two million five hundred thousand"


def test_polish_verification_code_in_context():
    line = "Your verification code is 311164."
    out = polish_numbers_for_tts(line, lang="en")
    assert "311164" not in out
    assert "three one one one six four" in out


def test_polish_money():
    line = "Invoice total: $1,234.56 due Friday."
    out = polish_numbers_for_tts(line, lang="en")
    assert "$" not in out
    assert "one thousand" in out
    assert "dollars" in out


def test_verification_code_line_french_email_english_tts():
    body = (
        "Code de vérification\r\n\r\nVotre code de vérification est :\r\n"
        "311164\r\n\r\nCe code expire dans 1 minute (mode test).\r\n"
    )
    line = verification_code_line(body, "Fwd: Code de vérification", lang="en")
    assert line is not None
    assert line.startswith("Your verification code is")
    assert "three one one one six four" in line
    assert "311164" not in line


def test_fallback_verification_code_not_sender_snippet():
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="OMAR EL <elkhalomar0@gmail.com>",
        subject="Fwd: Code de vérification",
        body=(
            "Code de vérification\r\n\r\nVotre code de vérification est :\r\n"
            "311164\r\n\r\nCe code expire dans 1 minute (mode test).\r\n"
        ),
    )
    line = fallback_speakable_line(event, lang="en")
    assert "OMAR EL" not in line
    assert "Code de vérification Votre" not in line
    assert "three one one one six four" in line


def test_cancellation_confirmation_code_french_email():
    body = (
        "Annulation de votre commande de cartes de visite\r\n\r\n"
        "Code de confirmation à 6 chiffres :\r\n593241\r\n\r\n"
        "Ce code expire dans 5 minutes."
    )
    subject = "Fwd: [Carte de visite] Code de confirmation pour l'annulation"
    assert extract_verification_code(body, subject) == "593241"
    line = verification_code_line(body, subject, lang="en")
    assert line is not None
    assert "cancellation confirmation code" in line
    assert "five nine three two four one" in line


def test_french_line_rejected_when_target_en():
    from voxpost.speakable_fallback import is_usable_summary, speakable_matches_target_lang

    bad = "OMAR EL: Annulation de votre commande de cartes de visite Code de."
    assert speakable_matches_target_lang(bad, "en") is False
    assert is_usable_summary(bad, lang="en") is False


def test_cancellation_fallback():
    from voxpost.events import NewMailEvent
    from voxpost.speakable_fallback import fallback_speakable_line

    event = NewMailEvent(
        account_id="a",
        message_id="m",
        thread_id="t",
        history_id="1",
        from_address="OMAR EL <elkhalomar0@gmail.com>",
        subject="Fwd: Code de confirmation pour l'annulation",
        body=(
            "Annulation de votre commande de cartes de visite\r\n\r\n"
            "Code de confirmation à 6 chiffres :\r\n593241\r\n"
        ),
    )
    line = fallback_speakable_line(event, lang="en")
    assert "five nine three two four one" in line
    assert "Annulation" not in line

