from voxpost.events import NewMailEvent
from tests.fixture_bodies import FORWARDED_FR_PHONE
from voxpost.speakable_fallback import (
    display_name,
    fallback_speakable_line,
    is_usable_summary,
    looks_like_json_echo,
    misattributes_forward,
)


def test_display_name_from_angle_brackets():
    assert display_name("Omar EL KHAL <elkhalomar@gmail.com>") == "Omar EL KHAL"


def test_is_usable_summary_rejects_email_label():
    assert is_usable_summary("E-mail:") is False
    assert (
        is_usable_summary(
            "The staging deploy failed around 9:45, indicating the migration step timed out."
        )
        is True
    )


def test_is_usable_summary_rejects_tts_meta_echo():
    assert is_usable_summary(
        "Asi Zaror is sending a summary to text-to-speech and read aloud once."
    ) is False


def test_is_usable_summary_rejects_email_addresses_and_vague_sender():
    assert is_usable_summary(
        "Asi noticed that the sender sent an email to partners@affiliaxe."
    ) is False


def test_is_usable_summary_rejects_single_name_overlap_hallucination():
    body = (
        "Bonjour Omar j'espère que tu vas bien je suis un client chez vous "
        "possible d'avoir votre numéro de téléphone merci"
    )
    assert (
        is_usable_summary(
            "Omar est un avocat à l'université de Ouagadougou.",
            source=body,
        )
        is False
    )


def test_is_usable_summary_rejects_clickbait_hallucination():
    body = (
        "Bonjour Omar j'espère que tu vas bien je suis un client chez vous "
        "possible d'avoir votre numéro de téléphone merci"
    )
    assert is_usable_summary("A l'aide, cliquez sur ce lien .", source=body) is False


def test_is_usable_summary_accepts_overlap_with_source():
    body = (
        "Bonjour Omar j'espère que tu vas bien je suis un client chez vous "
        "possible d'avoir votre numéro de téléphone merci"
    )
    assert (
        is_usable_summary(
            "Un client demande le numéro de téléphone de l'entreprise.",
            source=body,
        )
        is True
    )


def test_looks_like_json_echo():
    assert looks_like_json_echo('{"original_sender":"Sophie Martin","body":"La réunion"}') is True
    assert looks_like_json_echo("Sophie Martin moved the meeting to Thursday.") is False


def test_misattributes_forward_rejects_envelope_name():
    event = NewMailEvent(
        account_id="a@b.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject="Fwd:",
        body=FORWARDED_FR_PHONE,
    )
    assert misattributes_forward("Omar wrote, he wants his phone number.", event) is True
    assert misattributes_forward("Mustafa asks for a phone number.", event) is False


def test_is_usable_summary_rejects_json_echo_and_forward_misattribution():
    body = (
        "Bonjour Omar j'espère que tu vas bien je suis un client chez vous "
        "possible d'avoir votre numéro de téléphone merci"
    )
    event = NewMailEvent(
        account_id="a@b.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject="Fwd:",
        body=FORWARDED_FR_PHONE,
    )
    assert (
        is_usable_summary(
            '{"original_sender":"Sophie Martin","body":"La réunion est décalée"}',
            source=body,
        )
        is False
    )
    assert (
        is_usable_summary("Omar wrote, he wants his phone number.", source=body, event=event)
        is False
    )


def test_is_usable_summary_rejects_password_hallucination():
    body = (
        "We noticed a sign-in to your account from Berlin, Germany at 02:14 UTC. "
        "If this wasn't you, reset your password now."
    )
    assert is_usable_summary("It's almost impossible to trace your password.", source=body) is False
    event = NewMailEvent(
        account_id="a@b.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject="test",
        body="test email\r\n",
    )
    line = fallback_speakable_line(event)
    assert "Omar EL KHAL" in line
    assert "test" in line.lower()


def test_chat_lm_accepts_paraphrase_overlap():
    body = "Did you get the doc? Let me know today."
    assert (
        is_usable_summary(
            "Jordan Lee asks if you received the document.",
            source=body,
            chat_lm=True,
        )
        is True
    )


def test_chat_lm_accepts_short_ack():
    body = "Thanks — 3pm tomorrow works for me."
    assert (
        is_usable_summary(
            "Jordan Lee wants to sync at 3pm tomorrow.",
            source=body,
            chat_lm=True,
        )
        is True
    )


def test_chat_lm_still_rejects_hallucination():
    body = (
        "Bonjour Omar j'espère que tu vas bien je suis un client chez vous "
        "possible d'avoir votre numéro de téléphone merci"
    )
    assert (
        is_usable_summary(
            "Omar est un avocat à l'université de Ouagadougou.",
            source=body,
            chat_lm=True,
        )
        is False
    )


def test_fallback_uses_intent_not_long_body():
    event = NewMailEvent(
        account_id="a@b.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject="Fwd:",
        body=FORWARDED_FR_PHONE,
    )
    line = fallback_speakable_line(event)
    assert len(line.split()) <= 20
    assert "phone number" in line.lower()
    assert "j'espère" not in line.lower()
