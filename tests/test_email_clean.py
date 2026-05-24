"""Tests for email body cleaning before summarization."""

from voxpost.email_clean import clean_email_body, extract_forwarded_sender

FORWARDED_BODY = """---------- Forwarded message ---------
De : Asi Zaror <asi@affiliaxe.com>
Date: jeu. 17 oct. 2019 à 14:27
Subject: Hi Omar El Khal
To: <elkhalomar0@gmail.com>


Hi Omar El Khal,
Nice to e-meet you, My name is Asi and i would be your dedicated account
manager at affiliaXe.
I have noticed that you sent an email to partners@affiliaxe.com - How can I
help you?
Best regards
Asi
-- 

*Asi Zaror*
*Office:* +972.3.5463113
*Skype:* asi.affiliaxe@outlook.com
*Web:* www.affiliaXe.com <https://affiliaxe.com/>

This electronic mail transmission and any accompanying attachments contain
confidential information intended only for the use of the individual or
entity named above.
"""


def test_clean_forwarded_email_keeps_message():
    cleaned = clean_email_body(FORWARDED_BODY)
    assert "Nice to e-meet you" in cleaned
    assert "affiliaXe" in cleaned
    assert "confidential information" not in cleaned
    assert "https://" not in cleaned
    assert "Forwarded message" not in cleaned


def test_clean_forwarded_fr_phone_strips_empty_subject():
    from tests.fixture_bodies import FORWARDED_FR_PHONE

    cleaned = clean_email_body(FORWARDED_FR_PHONE)
    assert not cleaned.lower().startswith("subject:")
    assert "téléphone" in cleaned
    assert "Bonjour Omar" in cleaned


NESTED_FR_JUSTICE_FORWARD = """---------- Forwarded message ---------
From: Hamza Megdoud <hamzameg0512@gmail.com>
Date: Tue, May 12, 2026 at 11:46 AM
Subject: Fwd: Mail 2/2 – La réponse à votre demande d'extrait de casier
judiciaire bulletin n° 3 est disponible
To: <elkhalomar@gmail.com>


---------- Message transféré ---------
De : <noreply@justice.gouv.fr>
Date : mar. 12 mai 2026 à 08:20
Objet : Mail 2/2 – La réponse à votre demande d'extrait de casier
judiciaire bulletin n° 3 est disponible
À : <hamzameg0512@gmail.com>


Bonjour hamza megdoud,

Vous avez choisi une réponse dématérialisée à votre demande d'extrait de
casier judiciaire (bulletin n°3).

Vous disposez de 10 jours pour télécharger votre réponse.

Attention, vous ne pourrez télécharger que deux fois votre réponse sous
format PDF.

Cordialement,

Casier judiciaire national,
Ministère de la Justice
"""


def test_clean_nested_fr_justice_forward_keeps_body():
    cleaned = clean_email_body(NESTED_FR_JUSTICE_FORWARD)
    assert "Bonjour hamza megdoud" in cleaned
    assert "10 jours" in cleaned
    assert "deux fois" in cleaned
    assert "Ministère de la Justice" in cleaned
    assert "Message transféré" not in cleaned
    assert len(cleaned.split()) > 30


def test_extract_forwarded_sender_nested_uses_innermost():
    assert extract_forwarded_sender(NESTED_FR_JUSTICE_FORWARD) == "noreply@justice.gouv.fr"


def test_extract_forwarded_sender():
    assert extract_forwarded_sender(FORWARDED_BODY) == "Asi Zaror"
