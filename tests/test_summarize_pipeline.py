from unittest.mock import MagicMock, patch

import pytest

from voxpost.events import NewMailEvent
from voxpost.summarize import EmailSummarizer, sample_mail_event


@pytest.fixture(autouse=True)
def _force_transformers_seq2seq_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Pipeline tests mock seq2seq transformers; ignore host Ollama/chat config."""
    cfg_dir = tmp_path_factory.mktemp("voxpost_cfg")
    (cfg_dir / "voxpost.toml").write_text(
        """
[summarize]
backend = "transformers"
model = "csebuetnlp/mT5_multilingual_XLSum"

[speech]
mode = "fixed"
target_lang = "en"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("VOXPOST_CONFIG_DIR", str(cfg_dir))


def test_summarize_event_uses_model():
    event = sample_mail_event()
    summarizer = EmailSummarizer()
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = "Alex says staging deploy failed."
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        result = summarizer.summarize_event(event)

    assert result.speakable_line == "Alex says staging deploy failed."
    assert result.mail.message_id == event.message_id
    mock_model.generate.assert_called_once()


def test_summarize_event_polishes_abbreviations():
    event = sample_mail_event()
    summarizer = EmailSummarizer()
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = (
        "Staging deploy failed; team mtg moved to JEU at 2pm."
    )
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        result = summarizer.summarize_event(event)

    assert "meeting" in result.speakable_line
    # With default TTS lang=en, French day codes are not expanded to jeudi.
    assert "mtg" not in result.speakable_line


def test_summarize_event_rejects_vague_forward_summary():
    event = sample_mail_event()
    summarizer = EmailSummarizer()
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = (
        "Asi is the dedicated account manager at affiliaXe and has noticed "
        "that the sender sent an email to partners@affiliaxe."
    )
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        result = summarizer.summarize_event(event)

    assert "@" not in result.speakable_line
    assert "the sender" not in result.speakable_line.lower()
    assert "Alex Chen" in result.speakable_line


def test_summarize_event_rejects_tts_meta_echo():
    event = sample_mail_event()
    summarizer = EmailSummarizer()
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = (
        "Asi Zaror is sending a summary to text-to-speech and read aloud once "
        "to someone who cannot see the email."
    )
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        result = summarizer.summarize_event(event)

    assert "text-to-speech" not in result.speakable_line.lower()
    assert "Alex Chen" in result.speakable_line


def test_summarize_event_rejects_biography_hallucination():
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m-fwd2",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject="Fwd:",
        body=(
            "---------- Forwarded message ---------\r\n"
            "From: Mustafa Nadir Chekroun <chekrounnadir13@gmail.com>\r\n"
            "Date: Thu, May 21, 2026 at 5:11 PM\r\n"
            "Subject:\r\n"
            "To: Omar EL KHAL <elkhalomar@gmail.com>\r\n\r\n\r\n"
            "Bonjour Omar j'espère que tu vas bien je suis un client chez vous possible\r\n"
            "d'avoir votre numéro de téléphone merci\r\n"
        ),
    )
    summarizer = EmailSummarizer()
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = (
        "Omar est un avocat à l'université de Ouagadougou."
    )
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        result = summarizer.summarize_event(event)

    assert "avocat" not in result.speakable_line.lower()
    assert "Mustafa" in result.speakable_line
    assert "phone number" in result.speakable_line.lower()


def test_summarize_event_rejects_clickbait_hallucination():
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m-fwd",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject="Fwd:",
        body=(
            "---------- Forwarded message ---------\r\n"
            "From: Mustafa Nadir Chekroun <chekrounnadir13@gmail.com>\r\n"
            "Date: Thu, May 21, 2026 at 5:11 PM\r\n"
            "Subject:\r\n"
            "To: Omar EL KHAL <elkhalomar@gmail.com>\r\n\r\n\r\n"
            "Bonjour Omar j'espère que tu vas bien je suis un client chez vous possible\r\n"
            "d'avoir votre numéro de téléphone merci\r\n"
        ),
    )
    summarizer = EmailSummarizer()
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = "A l'aide, cliquez sur ce lien ."
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        result = summarizer.summarize_event(event)

    assert "cliquez sur ce lien" not in result.speakable_line.lower()
    assert "Mustafa" in result.speakable_line
    assert "phone number" in result.speakable_line.lower()


def test_summarize_event_fallback_on_weak_model_output():
    event = sample_mail_event()
    summarizer = EmailSummarizer()
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = "E-mail:"
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        result = summarizer.summarize_event(event)

    assert result.speakable_line != "E-mail:"
    assert "Alex Chen" in result.speakable_line
    assert (
        "Staging deploy failed" in result.speakable_line
        or "deploy" in result.speakable_line.lower()
    )


def test_summarize_event_keeps_long_mail_summarizer_on_soft_gate():
    """Long event mail must not collapse to a one-line intent fallback."""
    from voxpost.events import NewMailEvent

    body = (
        "Bonjour,\n\nTu rêves de ne plus avoir le trac et de savoir pitcher ton projet "
        "sur scène en quelques minutes ?\n\nLe programme Invest in Me te donne rendez-vous "
        "pour un nouvel atelier dédié à l'art de pitcher son projet en public au Garage "
        "Comedy Club de Marseille, le lundi 18 mai de 18h à 21h.\n\nPendant cette soirée, "
        "tu apprendras à structurer un discours clair et impactant.\n\nLes places sont "
        "limitées, pense à t'inscrire rapidement via le formulaire.\n"
    )
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        from_address="Village Start-up <startup@delta-festival.com>",
        subject="Atelier Invest In Me 18 mai 2026",
        body=body,
    )
    summarizer = EmailSummarizer()
    model_line = (
        "Village Start-up invites you to a public pitching workshop at Garage Comedy Club "
        "in Marseille on Monday May eighteenth from six p.m. to nine p.m.; register soon."
    )
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = model_line
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        with patch(
            "voxpost.summarize.is_usable_summary",
            return_value=False,
        ):
            result = summarizer.summarize_event(event)

    assert "workshop" in result.speakable_line.lower() or "pitch" in result.speakable_line.lower()
    assert "Marseille" in result.speakable_line or "Garage" in result.speakable_line
    assert result.speakable_line != "Village Start-up about booking a workshop or event."


def test_summarize_event_keeps_model_on_soft_gate_failure():
    """Lang or forward-attribution nits alone must not replace a good summarizer sentence."""
    event = sample_mail_event()
    summarizer = EmailSummarizer()
    model_line = (
        "Alex Chen says the staging deploy failed and asks you to check the pipeline logs."
    )
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = model_line
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        with patch(
            "voxpost.summarize.is_usable_summary",
            return_value=False,
        ):
            with patch(
                "voxpost.summarize.summary_overlaps_source",
                return_value=True,
            ):
                with patch(
                    "voxpost.summarize.entity_fallback_line",
                    return_value=None,
                ):
                    result = summarizer.summarize_event(event)

    assert model_line.split()[0] in result.speakable_line
    assert "pipeline" in result.speakable_line.lower()


def test_summarize_event_keeps_justice_bulletin_summarizer_on_soft_gate():
    """Long forwarded official mail must keep a descriptive summarizer line."""
    body = (
        "---------- Forwarded message ---------\r\n"
        "From: Hamza Megdoud <hamzameg0512@gmail.com>\r\n"
        "Date: Tue, May 12, 2026 at 11:46 AM\r\n"
        "Subject: Fwd: Mail 2/2 – La réponse à votre demande d'extrait de casier "
        "judiciaire bulletin n° 3 est disponible\r\n"
        "To: <elkhalomar@gmail.com>\r\n\r\n"
        "---------- Message transféré ---------\r\n"
        "De : <noreply@justice.gouv.fr>\r\n"
        "Objet : Mail 2/2 – La réponse à votre demande d'extrait de casier "
        "judiciaire bulletin n° 3 est disponible\r\n\r\n"
        "Bonjour hamza megdoud,\r\n\r\n"
        "Vous avez choisi une réponse dématérialisée à votre demande d'extrait de "
        "casier judiciaire (bulletin n°3).\r\n\r\n"
        "Pour des raisons de sécurité, vous devrez saisir vos éléments d'identité "
        "et la référence communiquée dans notre premier courriel.\r\n\r\n"
        "Vous disposez de 10 jours pour télécharger votre réponse.\r\n\r\n"
        "Attention, vous ne pourrez télécharger que deux fois votre réponse sous "
        "format PDF.\r\n\r\n"
        "Cliquez sur le bouton ci-dessous pour obtenir votre réponse.\r\n\r\n"
        "Cordialement,\r\nCasier judiciaire national, Ministère de la Justice\r\n"
    )
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m-justice",
        thread_id="t1",
        history_id="1",
        from_address="Omar EL KHAL <elkhalomar@gmail.com>",
        subject=(
            "Fwd: Mail 2/2 – La réponse à votre demande d'extrait de casier "
            "judiciaire bulletin n° 3 est disponible"
        ),
        body=body,
    )
    summarizer = EmailSummarizer()
    model_line = (
        "France's criminal record service says bulletin three is ready to download. "
        "You have ten days, need identity details and the reference from the first "
        "email, and the PDF can only be downloaded twice."
    )
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = model_line
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        with patch(
            "voxpost.summarize.is_usable_summary",
            return_value=False,
        ):
            result = summarizer.summarize_event(event)

    assert "Omar" not in result.speakable_line or "criminal record" in result.speakable_line.lower()
    assert "ten days" in result.speakable_line.lower() or "10" in result.speakable_line
    assert "bulletin" in result.speakable_line.lower() or "criminal record" in result.speakable_line.lower()
    assert result.speakable_line != "Omar El Khalar sent a message saying the judicial bulletin is available."


def test_summarize_event_keeps_assistant_style_booking_on_soft_gate():
    """Assistant-style booking confirmation must survive soft gate on long mail."""
    body = (
        "Dear guest,\n\nThank you for booking with us. Your reservation is confirmed.\n\n"
        "Hotel: Marina Bay Suites\n"
        "Check-in: Friday 14 June 2026 at 3 p.m.\n"
        "Check-out: Sunday 16 June 2026 at 11 a.m.\n"
        "Guests: 2 adults\n"
        "Reference: MB-48291\n\n"
        "Please bring a photo ID at check-in. Free cancellation until 48 hours before arrival.\n"
        "If you need to change dates, reply to this email or use the manage booking link.\n"
    )
    event = NewMailEvent(
        account_id="elkhalomar@gmail.com",
        message_id="m-booking",
        thread_id="t1",
        history_id="1",
        from_address="Marina Bay Suites <reservations@marinabay.example>",
        subject="Booking confirmation — Marina Bay Suites, 14–16 June",
        body=body,
    )
    summarizer = EmailSummarizer()
    model_line = (
        "Your booking confirmation for Marina Bay Suites on Friday June fourteenth has arrived; "
        "check-in is at three p.m. and you can cancel free until forty-eight hours before."
    )
    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = model_line
    mock_model = MagicMock()
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.return_value = {"input_ids": MagicMock()}

    with patch.object(summarizer, "_ensure_loaded"):
        summarizer._pipe = (mock_tokenizer, mock_model)
        with patch(
            "voxpost.summarize.is_usable_summary",
            return_value=False,
        ):
            result = summarizer.summarize_event(event)

    assert "booking" in result.speakable_line.lower()
    assert "confirmation" in result.speakable_line.lower() or "confirmed" in result.speakable_line.lower()
    assert "Marina Bay" in result.speakable_line or "Friday" in result.speakable_line
    assert result.speakable_line != "Marina Bay Suites about booking a hotel or event."
