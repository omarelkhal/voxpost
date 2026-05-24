"""Overlap and fallback helpers for speakable-line quality gates."""

from __future__ import annotations

import re

from voxpost.events import NewMailEvent

# Cross-language / paraphrase token groups for chat-LM overlap checks.
_PARAPHRASE_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"doc", "document", "docs"}),
    frozenset({"phone", "telephone", "téléphone", "numero", "numéro", "number"}),
    frozenset({"refund", "remboursement"}),
    frozenset({"package", "paquete", "paquet"}),
    frozenset({"meeting", "reunion", "réunion", "gesprek", "sync"}),
    frozenset({"tomorrow", "mañana", "demain"}),
    frozenset({"delivery", "entrega", "livr", "entrega"}),
    frozenset({"cancel", "canceled", "cancelled", "annul", "annulé"}),
    frozenset({"invoice", "facture", "fatura", "billing"}),
    frozenset({"deploy", "deployment", "staging", "migration"}),
    frozenset({"password", "reset", "sign", "signin", "sign-in"}),
    frozenset({"order", "commande"}),
    frozenset({"interview", "sollicitatie", "gesprek"}),
    frozenset({"thanks", "thank", "works"}),
    frozenset({"wrong", "mauvais", "model", "modèle", "modele"}),
    frozenset({"home", "casa", "house"}),
    frozenset({"tax", "steuer", "bescheid", "finanzamt"}),
    frozenset({"hotel", "reserva", "reservation", "booking", "confirm"}),
    frozenset({"review", "pull", "request"}),
    frozenset({"rent", "lease", "tenant"}),
    frozenset({"dinner", "cena", "invite", "invitation"}),
    frozenset({"school", "closed", "remote", "snow", "weather"}),
    frozenset({"dental", "cleaning", "appointment", "reminder"}),
    frozenset({"delay", "delayed", "eta", "ship", "shipment", "customs"}),
    frozenset({"received", "get", "got"}),
)

_BOILERPLATE_BODIES = frozenset(
    {
        "view this message in your browser. manage preferences.",
        "(empty body)",
        "(empty)",
    }
)

_INTENT_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("téléphone", "telephone", "phone", "numéro", "numero"), "asks for your phone number"),
    (("remboursement", "refund"), "requests a refund"),
    (("deploy", "migration", "pipeline"), "reports a deploy problem"),
    (("invoice", "due", "payment", "pay"), "about an invoice or payment"),
    (("sign-in", "sign in", "password", "reset"), "about a sign-in or password reset"),
    (("paquete", "package", "delivery", "entrega"), "about a package delivery"),
    (("réunion", "reunion", "meeting"), "about a meeting change"),
    (("order", "99281"), "about a missing order"),
    (("gesprek", "interview", "sollicitatie"), "invites you to an interview"),
    (("steuer", "bescheid", "tax"), "about a tax notice"),
    (("canceled", "cancelled", "cancel", "ua882", "flight"), "about a canceled flight"),
    (("doc", "document"), "asking if you got a document"),
)


def expand_paraphrase_tokens(tokens: set[str]) -> set[str]:
    out = set(tokens)
    for group in _PARAPHRASE_GROUPS:
        if tokens & group:
            out |= group
    return out


def shared_digit_tokens(a: str, b: str) -> bool:
    nums_a = set(re.findall(r"\d{2,}", a))
    nums_b = set(re.findall(r"\d{2,}", b))
    return bool(nums_a & nums_b)


def is_mostly_english_ascii(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    ascii_count = sum(1 for c in letters if ord(c) < 128)
    return ascii_count / len(letters) >= 0.92


def is_cross_language_summary(summary: str, source: str) -> bool:
    """English-ish summary of a non-English or mixed source body."""
    if not source.strip():
        return False
    return is_mostly_english_ascii(summary) and not is_mostly_english_ascii(source)


def resolve_author_name(event: NewMailEvent) -> str:
    from voxpost.email_clean import extract_forwarded_sender

    subject = (event.subject or "").strip().lower()
    forwarded = extract_forwarded_sender(event.body or "")
    if forwarded and subject.startswith(("fwd:", "fw:", "tr:", "re:")):
        return forwarded
    from voxpost.speakable_fallback import display_name

    return display_name(event.from_address)


def summary_names_author(summary: str, event: NewMailEvent) -> bool:
    author = resolve_author_name(event)
    if not author:
        return False
    lower = summary.lower()
    first = author.split()[0].lower()
    if len(first) >= 3 and re.search(rf"\b{re.escape(first)}\b", lower):
        return True
    return author.lower() in lower


def infer_short_intent(event: NewMailEvent, *, body: str, subject: str) -> str | None:
    haystack = f"{subject} {body}".lower()
    for needles, phrase in _INTENT_HINTS:
        if any(n in haystack for n in needles):
            return phrase
    return None


def is_boilerplate_body(body: str) -> bool:
    normalized = body.strip().lower()
    if not normalized:
        return True
    if normalized in _BOILERPLATE_BODIES:
        return True
    return len(normalized.split()) <= 5


def short_subject_intent(subject: str) -> str:
    text = subject.strip()
    for prefix in ("fwd:", "fw:", "re:", "tr:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :].strip()
    if not text:
        return "forwarded a message"
    if len(text.split()) > 12:
        return " ".join(text.split()[:12]) + "…"
    return text
