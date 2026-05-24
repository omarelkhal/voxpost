"""Diverse email fixtures for speakable-line quality evaluation.

Core set (11): forwards, short acks, invoices, security, newsletters, etc.
Extended set (13+): tax letters, hotel confirmations, OOO autoreplies, GitHub
notifications, rent notices, Italian invites, bullet-list API mail, subject-only
flight cancel, angry caps complaints, Dutch HR, school alerts, dental reminders,
mixed JP/EN vendor delays — intentionally unlike the core scenarios.

Do not tune summarizer gates or prompts against this file alone; add new fixtures
when a production failure pattern appears.
"""

from __future__ import annotations

from dataclasses import dataclass

from voxpost.attachments import AttachmentInfo
from voxpost.events import NewMailEvent

FORWARDED_AFFILIAXE = """---------- Forwarded message ---------
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
"""

FORWARDED_FR_PHONE = """---------- Forwarded message ---------
From: Mustafa Nadir Chekroun <chekrounnadir13@gmail.com>
Date: Thu, May 21, 2026 at 5:11 PM
Subject:
To: Omar EL KHAL <elkhalomar@gmail.com>


Bonjour Omar j'espère que tu vas bien je suis un client chez vous possible
d'avoir votre numéro de téléphone merci
"""


@dataclass(frozen=True)
class SpeechCheckCase:
    """One email scenario and what a good spoken line should reflect."""

    case_id: str
    label: str
    intent: str
    event: NewMailEvent
    must_mention_any: tuple[str, ...] = ()
    must_not_mention: tuple[str, ...] = ()
    max_words: int = 40


def _base(**kwargs) -> NewMailEvent:
    defaults = dict(
        account_id="eval@test.local",
        message_id="eval-msg",
        thread_id="eval-thread",
        history_id="1",
    )
    defaults.update(kwargs)
    return NewMailEvent(**defaults)


def speech_check_cases() -> tuple[SpeechCheckCase, ...]:
    return (
        SpeechCheckCase(
            case_id="fr_forward_phone",
            label="French forward — client asks for phone number",
            intent="Customer Mustafa asks Omar for a phone number.",
            event=_base(
                message_id="fr-fwd-phone",
                from_address="Omar EL KHAL <elkhalomar@gmail.com>",
                subject="Fwd:",
                body=FORWARDED_FR_PHONE,
            ),
            must_mention_any=(
                "téléphone",
                "telephone",
                "numéro",
                "numero",
                "phone",
                "number",
                "client",
                "mustafa",
            ),
            must_not_mention=(
                "avocat",
                "ouagadougou",
                "cliquez sur ce lien",
                "offshore pipeline",
                "université",
            ),
        ),
        SpeechCheckCase(
            case_id="en_deploy_alert",
            label="English — staging deploy failed",
            intent="Staging deploy failed; migration timed out; check logs.",
            event=_base(
                message_id="en-deploy",
                from_address="Alex Chen <alex@company.com>",
                subject="Staging deploy failed",
                body=(
                    "Hey — the staging deploy failed around 9:45. "
                    "Looks like the migration step timed out. "
                    "Can you check the pipeline logs when you get a chance?"
                ),
            ),
            must_mention_any=("deploy", "migration", "staging", "failed", "timeout", "timed out"),
            must_not_mention=("offshore", "click here", "full transcript"),
        ),
        SpeechCheckCase(
            case_id="en_short_ack",
            label="English — short acknowledgment",
            intent="Quick thanks and confirm 3pm meeting.",
            event=_base(
                message_id="en-short",
                from_address="Jordan Lee <jordan@team.io>",
                subject="Re: sync",
                body="Thanks — 3pm tomorrow works for me.",
            ),
            must_mention_any=("3", "tomorrow", "thanks", "works", "sync", "pm"),
            max_words=25,
        ),
        SpeechCheckCase(
            case_id="fr_meeting_move",
            label="French — meeting moved to Thursday",
            intent="Meeting moved to Thursday 14h, room change.",
            event=_base(
                message_id="fr-meeting",
                from_address="Sophie Martin <sophie@corp.fr>",
                subject="Report réunion",
                body=(
                    "Bonjour, la réunion est décalée à jeudi 14h. "
                    "On se retrouve en salle B12 au lieu de A3. Merci."
                ),
            ),
            must_mention_any=(
                "jeudi",
                "thursday",
                "14",
                "réunion",
                "reunion",
                "meeting",
                "salle",
                "room",
                "décal",
                "moved",
            ),
            must_not_mention=("cliquez", "click here", "ouagadougou"),
        ),
        SpeechCheckCase(
            case_id="en_invoice_due",
            label="English — invoice payment due",
            intent="Invoice #4421 due Friday; pay via portal.",
            event=_base(
                message_id="en-invoice",
                from_address="Billing <billing@vendor.com>",
                subject="Invoice #4421 due Friday",
                body=(
                    "Your invoice #4421 for €1,240 is due this Friday. "
                    "Pay at portal.vendor.com or reply if you need a PO."
                ),
                has_attachments=True,
                attachment_count=1,
                attachments=(
                    AttachmentInfo(
                        filename="invoice-4421.pdf",
                        mime_type="application/pdf",
                        size_bytes=88000,
                    ),
                ),
            ),
            must_mention_any=("invoice", "4421", "friday", "due", "pay", "payment"),
            must_not_mention=("click here to subscribe", "offshore"),
        ),
        SpeechCheckCase(
            case_id="en_forward_partner",
            label="English forward — account manager intro",
            intent="Asi from affiliaXe offers help as account manager.",
            event=_base(
                message_id="en-fwd-partner",
                from_address="Omar EL KHAL <elkhalomar@gmail.com>",
                subject="Fwd: Hi Omar El Khal",
                body=FORWARDED_AFFILIAXE,
            ),
            must_mention_any=("asi", "affiliaxe", "account manager", "help"),
            must_not_mention=("partners@", "confidential information"),
        ),
        SpeechCheckCase(
            case_id="es_delivery",
            label="Spanish — package delivery window",
            intent="Package arrives tomorrow 9-12; someone must be home.",
            event=_base(
                message_id="es-delivery",
                from_address="Logística <envios@correo.es>",
                subject="Entrega mañana",
                body=(
                    "Hola, su paquete llegará mañana entre 9:00 y 12:00. "
                    "Debe haber alguien en casa para recibirlo."
                ),
            ),
            must_mention_any=(
                "paquete",
                "package",
                "mañana",
                "tomorrow",
                "9",
                "12",
                "casa",
                "home",
                "entrega",
                "delivery",
            ),
            must_not_mention=("click here", "cliquez"),
        ),
        SpeechCheckCase(
            case_id="en_security_alert",
            label="English — sign-in from new device",
            intent="New sign-in from Berlin; reset password if not you.",
            event=_base(
                message_id="en-security",
                from_address="Security <security@service.com>",
                subject="New sign-in from Berlin",
                body=(
                    "We noticed a sign-in to your account from Berlin, Germany "
                    "at 02:14 UTC. If this wasn't you, reset your password now."
                ),
            ),
            must_mention_any=("sign", "berlin", "password", "account", "reset"),
            must_not_mention=(
                "subscribe",
                "unsubscribe newsletter",
                "impossible to trace",
            ),
        ),
        SpeechCheckCase(
            case_id="fr_complaint",
            label="French — product complaint",
            intent="Customer unhappy; wants refund within 48 hours.",
            event=_base(
                message_id="fr-complaint",
                from_address="Lucie Dupont <lucie.dupont@gmail.com>",
                subject="Remboursement",
                body=(
                    "Bonjour, j'ai reçu le mauvais modèle. "
                    "Je demande un remboursement sous 48 heures svp."
                ),
            ),
            must_mention_any=(
                "remboursement",
                "refund",
                "mauvais",
                "wrong",
                "modèle",
                "modele",
                "model",
                "48",
            ),
            must_not_mention=("cliquez sur ce lien", "avocat"),
        ),
        SpeechCheckCase(
            case_id="en_minimal_ping",
            label="English — one-line ping",
            intent="Sender asks if you received the doc.",
            event=_base(
                message_id="en-minimal",
                from_address="Sam <sam@docs.co>",
                subject="doc",
                body="Did you get the doc?",
            ),
            must_mention_any=("doc", "get", "received", "sam"),
            max_words=20,
        ),
        SpeechCheckCase(
            case_id="en_newsletter_noise",
            label="English — newsletter marketing (noise)",
            intent="Marketing promo — ideally brief or filtered; not a full readout.",
            event=_base(
                message_id="en-newsletter",
                from_address="Deals Weekly <news@shop.example>",
                subject="🔥 50% OFF everything this weekend!!!",
                body=(
                    "Don't miss our biggest sale! Shop now and save 50% on all items. "
                    "Unsubscribe at the bottom. Click here for deals."
                ),
            ),
            must_mention_any=("sale", "50", "shop", "weekend", "off", "deals"),
            must_not_mention=("unsubscribe link below",),
            max_words=30,
        ),
        # --- Extended fixtures (diverse; avoid overlapping the 11 core scenarios) ---
        SpeechCheckCase(
            case_id="de_tax_notice",
            label="German — tax assessment notice",
            intent="Finanzamt sent 2025 income tax assessment; objection deadline applies.",
            event=_base(
                message_id="de-tax",
                from_address="Finanzamt München <finanzamt@example.de>",
                subject="Steuerbescheid 2025 — Einkommensteuer",
                body=(
                    "Sehr geehrter Herr EL KHAL, anbei erhalten Sie Ihren "
                    "Einkommensteuerbescheid für 2025. Einspruchsfrist: 4 Wochen "
                    "ab Zustellung. Bei Rückfragen steht Ihnen unser Bürgerbüro zur Verfügung."
                ),
            ),
            must_mention_any=(
                "steuer",
                "tax",
                "bescheid",
                "assessment",
                "2025",
                "einspruch",
                "objection",
                "finanzamt",
            ),
            must_not_mention=("click here", "50% off", "offshore"),
        ),
        SpeechCheckCase(
            case_id="pt_hotel_confirm",
            label="Portuguese — hotel booking confirmation",
            intent="Booking confirmed in Porto; check-in Friday; late arrival noted.",
            event=_base(
                message_id="pt-hotel",
                from_address="Reservas <reservas@hotelporto.pt>",
                subject="Confirmação — Hotel Ribeira, 12–14 Jun",
                body=(
                    "Olá Omar, a sua reserva está confirmada para 12 a 14 de junho. "
                    "Check-in a partir das 15h. Informámos chegada tardia (~23h). "
                    "Pequeno-almoço incluído."
                ),
            ),
            must_mention_any=(
                "reserva",
                "booking",
                "confirm",
                "junho",
                "june",
                "check",
                "porto",
                "hotel",
            ),
            must_not_mention=("cliquez", "unsubscribe newsletter"),
        ),
        SpeechCheckCase(
            case_id="en_ooo_autoreply",
            label="English — out-of-office auto-reply",
            intent="Sender away until June 2; contact Jane for urgent items.",
            event=_base(
                message_id="en-ooo",
                from_address="Marcus Webb <marcus@agency.io>",
                subject="Out of office Re: contract draft",
                body=(
                    "I'm out of the office until Monday, June 2 with limited email access. "
                    "For urgent matters contact Jane Park at jane@agency.io. "
                    "This is an automated response."
                ),
            ),
            must_mention_any=(
                "out",
                "office",
                "june",
                "jane",
                "urgent",
                "automated",
                "away",
            ),
            must_not_mention=("jane@", "marcus@"),
        ),
        SpeechCheckCase(
            case_id="en_github_pr",
            label="English — GitHub pull request review",
            intent="Review requested on PR #882 auth refactor before release.",
            event=_base(
                message_id="en-github",
                from_address="GitHub <notifications@github.com>",
                subject="[repo] Review requested on PR #882: refactor auth middleware",
                body=(
                    "@you were requested to review pull request #882 by @devon. "
                    "Refactors JWT validation and session refresh. Target branch: main. "
                    "Please review before Friday's release cut."
                ),
            ),
            must_mention_any=(
                "review",
                "882",
                "pull",
                "auth",
                "release",
                "friday",
                "refactor",
            ),
            must_not_mention=("reset your password", "invoice due"),
        ),
        SpeechCheckCase(
            case_id="en_rent_increase",
            label="English — landlord rent increase letter",
            intent="Rent rises 8% from July 1; new lease rider attached.",
            event=_base(
                message_id="en-rent",
                from_address="Oak Street Properties <leasing@oakstreet.example>",
                subject="Notice: rent adjustment effective July 1",
                body=(
                    "Dear tenant, per your lease section 14, monthly rent will increase "
                    "by 8% effective July 1. The new amount is $1,728. A signed rider "
                    "is attached; return within 14 days."
                ),
                has_attachments=True,
                attachment_count=1,
                attachments=(
                    AttachmentInfo(
                        filename="lease-rider-2026.pdf",
                        mime_type="application/pdf",
                    ),
                ),
            ),
            must_mention_any=("rent", "8", "july", "lease", "increase", "728", "rider"),
            must_not_mention=("staging deploy", "package delivery"),
        ),
        SpeechCheckCase(
            case_id="it_dinner_invite",
            label="Italian — informal dinner invitation",
            intent="Invite to dinner Saturday 8pm at Trattoria da Luca.",
            event=_base(
                message_id="it-dinner",
                from_address="Giulia Rossi <giulia.rossi@gmail.com>",
                subject="Cena sabato?",
                body=(
                    "Ciao Omar! Sabato sera ci vediamo da Luca alle 20:00? "
                    "Prenoto per 6 persone. Fammi sapere se vegetariano per te."
                ),
            ),
            must_mention_any=(
                "cena",
                "dinner",
                "sabato",
                "saturday",
                "20",
                "luca",
                "vegetar",
            ),
            must_not_mention=("steuerbescheid", "deploy failed"),
        ),
        SpeechCheckCase(
            case_id="en_api_bullet_list",
            label="English — three numbered API questions",
            intent="Client asks three distinct API migration questions.",
            event=_base(
                message_id="en-bullets",
                from_address="Priya Nair <priya@clientcorp.com>",
                subject="API migration — three blockers",
                body=(
                    "Hi team,\n"
                    "1) Will v2 webhooks stay supported through Q3?\n"
                    "2) What's the rate limit on bulk export?\n"
                    "3) Do sandbox keys rotate automatically?\n"
                    "Need answers before our board meeting Tuesday.\n"
                    "— Priya"
                ),
            ),
            must_mention_any=(
                "webhook",
                "rate",
                "export",
                "sandbox",
                "api",
                "tuesday",
                "board",
                "question",
            ),
            must_not_mention=("50% off", "steuer"),
        ),
        SpeechCheckCase(
            case_id="en_subject_only_flight",
            label="English — subject-only flight cancellation",
            intent="United canceled flight UA882; body is empty boilerplate.",
            event=_base(
                message_id="en-flight-subj",
                from_address="United Airlines <noreply@united.com>",
                subject="Flight UA882 to ORD on May 22 canceled — rebook options",
                body="View this message in your browser. Manage preferences.",
            ),
            must_mention_any=(
                "ua882",
                "882",
                "canceled",
                "cancelled",
                "flight",
                "rebook",
                "ord",
                "may",
            ),
            must_not_mention=("steuer", "deploy"),
            max_words=25,
        ),
        SpeechCheckCase(
            case_id="en_angry_order",
            label="English — angry ALL CAPS order complaint",
            intent="Customer furious; order #99281 missing; demands callback today.",
            event=_base(
                message_id="en-angry",
                from_address="Chris Morgan <chris.m@email.com>",
                subject="WHERE IS MY ORDER",
                body=(
                    "THIS IS UNACCEPTABLE. I PAID FOR ORDER #99281 TWO WEEKS AGO "
                    "AND STILL NOTHING. CALL ME TODAY OR I CHARGE BACK."
                ),
            ),
            must_mention_any=(
                "99281",
                "order",
                "call",
                "charge",
                "weeks",
                "paid",
            ),
            must_not_mention=("nice to e-meet", "affiliaxe"),
            max_words=25,
        ),
        SpeechCheckCase(
            case_id="nl_interview_invite",
            label="Dutch — job interview invitation",
            intent="Interview Tuesday 10:00 at HQ; bring ID and CV.",
            event=_base(
                message_id="nl-interview",
                from_address="HR TechVision <hr@techvision.nl>",
                subject="Uitnodiging sollicitatiegesprek — Backend Engineer",
                body=(
                    "Beste Omar, graag nodigen wij u uit voor een gesprek op dinsdag "
                    "om 10:00 in ons kantoor (Herengracht 100). Neem een geldig ID en "
                    "CV mee. Bevestig uw aanwezigheid."
                ),
            ),
            must_mention_any=(
                "interview",
                "gesprek",
                "dinsdag",
                "tuesday",
                "10",
                "cv",
                "herengracht",
                "engineer",
            ),
            must_not_mention=("deploy", "invoice 4421"),
        ),
        SpeechCheckCase(
            case_id="en_school_snow_day",
            label="English — school closure alert",
            intent="School closed tomorrow due to snow; classes remote on Teams.",
            event=_base(
                message_id="en-school",
                from_address="Lincoln Elementary <office@lincoln-edu.example>",
                subject="Emergency: school closed Thursday — remote learning",
                body=(
                    "Due to severe weather, Lincoln Elementary will be closed Thursday. "
                    "Students should join remote classes via Teams at 9:00 AM. "
                    "Hot lunch program suspended."
                ),
            ),
            must_mention_any=(
                "closed",
                "snow",
                "weather",
                "thursday",
                "remote",
                "teams",
                "school",
            ),
            must_not_mention=("rent increase", "github"),
        ),
        SpeechCheckCase(
            case_id="en_dentist_reminder",
            label="English — dental appointment reminder",
            intent="Reminder for cleaning Monday 4pm; call to reschedule if needed.",
            event=_base(
                message_id="en-dentist",
                from_address="Bright Smile Dental <reminders@brightsmile.example>",
                subject="Reminder: cleaning appointment Mon May 26 at 4:00 PM",
                body=(
                    "Hi Omar, reminder for your dental cleaning Monday May 26 at 4:00 PM "
                    "with Dr. Patel. Reply or call (555) 019-8832 to reschedule."
                ),
            ),
            must_mention_any=(
                "dental",
                "cleaning",
                "monday",
                "may",
                "26",
                "4",
                "patel",
                "reschedule",
            ),
            must_not_mention=("order #99281", "steuer"),
        ),
        SpeechCheckCase(
            case_id="ja_en_mixed_vendor",
            label="Mixed JP/EN — vendor shipment delay",
            intent="Tokyo supplier says shipment delayed; new ETA June 5.",
            event=_base(
                message_id="ja-mixed",
                from_address="Tanaka Trading <export@tanaka-trading.co.jp>",
                subject="Re: PO-7781 — shipment delay / 出荷遅延",
                body=(
                    "Omar-san, 申し訳ございません。PO-7781 will ship late due to customs. "
                    "New ETA: June 5. We will absorb express fees. "
                    "Please confirm receipt of this update."
                ),
            ),
            must_mention_any=(
                "7781",
                "delay",
                "june",
                "ship",
                "customs",
                "eta",
                "po",
            ),
            must_not_mention=("50% off everything", "github pr"),
        ),
    )
