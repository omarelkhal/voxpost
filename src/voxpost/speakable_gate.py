"""Overlap and fallback helpers for chat-LM summarizer quality gates."""

from __future__ import annotations

import re
import unicodedata

from voxpost.events import NewMailEvent
from voxpost.speakable_fallback import display_name

# Equivalence classes for cross-language / paraphrase overlap (chat LMs).
_PARAPHRASE_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"doc", "document", "documents", "file", "files"}),
    frozenset({"get", "got", "receive", "received", "receiving"}),
    frozenset({"refund", "remboursement", "reimburse", "reimbursement"}),
    frozenset({"phone", "telephone", "téléphone", "telefone", "numero", "numéro", "number"}),
    frozenset({"package", "paquete", "paquet", "parcel", "shipment"}),
    frozenset({"tomorrow", "mañana", "manha", "demain"}),
    frozenset({"thursday", "jeudi", "jueves", "quinta"}),
    frozenset({"meeting", "réunion", "reunion", "mtg", "gesprek"}),
    frozenset({"room", "salle", "sala", "kantoor"}),
    frozenset({"delivery", "entrega", "livraison", "llegará", "llegara", "arrives"}),
    frozenset({"home", "casa", "house"}),
    frozenset({"invoice", "factura", "fatura", "rechnung"}),
    frozenset({"password", "reset", "sign", "signed", "signin", "sign-in"}),
    frozenset({"deploy", "deployment", "staging", "migration", "pipeline"}),
    frozenset({"tax", "steuer", "bescheid", "assessment", "einkommensteuer", "finanzamt"}),
    frozenset({"order", "pedido", "commande"}),
    frozenset({"interview", "sollicitatie", "gesprek", "engineer"}),
    frozenset({"dental", "cleaning", "dentist", "appointment"}),
    frozenset({"cancel", "canceled", "cancelled", "cancellation", "rebook"}),
    frozenset({"wrong", "mauvais", "model", "modèle", "modele"}),
    frozenset({"client", "customer", "cliente"}),
    frozenset({"sync", "meeting", "works", "thanks", "thank"}),
    frozenset({"application", "candidate", "declined", "rejected", "position", "role"}),
)

_SHORT_BODY_WORDS = 12
_FALLBACK_MAX_SPOKEN_WORDS = 18

_SPAM_TEMPLATE_RE = re.compile(
    r"^this looks like spam about (.+?)\.?$",
    re.IGNORECASE,
)

_LEGACY_HEDGE_RE = re.compile(
    r"^it's about (.+?)\.\s*worth checking",
    re.IGNORECASE,
)

_BRIEFING_FIRM_SPAM_RE = re.compile(
    r"^(?P<briefing>you received an email about .+?)\.\s*this looks like spam\.?$",
    re.IGNORECASE,
)

_BRIEFING_ALREADY_HEDGED_RE = re.compile(
    r"^you received an email about .+\.\s*worth checking",
    re.IGNORECASE,
)

_FIRM_SPAM_TAIL_RE = re.compile(
    r"\.\s*this looks like spam\.?\s*$",
    re.IGNORECASE,
)

_SPAM_HEDGE_SUFFIX = "Worth checking — it might be spam."


def _received_email_briefing(topic: str) -> str:
    """Assistant voice for mail the listener has not opened yet."""
    cleaned = topic.strip().rstrip(".")
    if not cleaned:
        return "You received an email."
    return f"You received an email about {cleaned}."


def adjust_misapplied_spam_template(
    line: str,
    event: NewMailEvent,
    *,
    normalized_body: str | None = None,
) -> str:
    """
    Rewrite spam-template model lines into unseen-mail briefing shape.

    Summary first (what arrived), soft spam hedge last. Never assert spam —
    the classifier is unreliable; always hedge.
    """
    del event, normalized_body  # topic extraction is from the model line only
    text = line.strip()

    firm_briefing = _BRIEFING_FIRM_SPAM_RE.match(text)
    if firm_briefing:
        return f"{firm_briefing.group('briefing')}. {_SPAM_HEDGE_SUFFIX}"

    if _BRIEFING_ALREADY_HEDGED_RE.match(text):
        return text

    topic: str | None = None
    match = _SPAM_TEMPLATE_RE.match(text)
    if match:
        topic = match.group(1).strip().rstrip(".")
    else:
        hedge = _LEGACY_HEDGE_RE.match(text)
        if hedge:
            topic = hedge.group(1).strip().rstrip(".")
        else:
            if _FIRM_SPAM_TAIL_RE.search(text):
                return _FIRM_SPAM_TAIL_RE.sub(f". {_SPAM_HEDGE_SUFFIX}", text)
            return text

    briefing = _received_email_briefing(topic or "")
    return f"{briefing} {_SPAM_HEDGE_SUFFIX}"


def normalize_token(word: str) -> str:
    """Lowercase ASCII-ish token for overlap comparison."""
    text = word.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text)


def expand_paraphrase_tokens(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for group in _PARAPHRASE_GROUPS:
        if expanded & group:
            expanded |= group
    return expanded


def token_set(text: str, *, min_len: int = 3) -> set[str]:
    raw = {normalize_token(w) for w in re.findall(r"\w+", text.lower())}
    return {t for t in raw if len(t) >= min_len}


def sender_first_name(event: NewMailEvent) -> str | None:
    from voxpost.email_clean import clean_email_body, extract_forwarded_sender
    from voxpost.email_entities import extract_email_entities
    from voxpost.summarizer_context import detect_is_forward

    cleaned = clean_email_body(event.body or "")
    entities = extract_email_entities(cleaned, subject=event.subject)
    if entities.signatory_name:
        return entities.signatory_name.split()[0]
    if detect_is_forward(event):
        inner = extract_forwarded_sender(event.body or "")
        if inner:
            return inner.split()[0]
    name = display_name(event.from_address)
    return name.split()[0] if name else None


def summary_mentions_sender(summary: str, event: NewMailEvent | None) -> bool:
    if not event:
        return False
    first = sender_first_name(event)
    if not first or len(first) < 3:
        return False
    return first.lower() in summary.lower()


def summary_overlaps_source_chat(
    summary: str,
    source: str,
    *,
    event: NewMailEvent | None = None,
) -> bool:
    """
    Looser overlap for instruction-tuned chat models (English summary, any body lang).

    Still rejects unrelated hallucinations when no sender anchor and no paraphrase link.
    """
    if summary_mentions_sender(summary, event):
        src_t = token_set(source, min_len=3)
        out_t = expand_paraphrase_tokens(token_set(summary, min_len=3))
        if src_t & out_t:
            return True
        # Named sender + substantive summary without shared tokens: allow short mail.
        if len(source.split()) <= _SHORT_BODY_WORDS and len(summary.split()) >= 4:
            return True

    src = expand_paraphrase_tokens(token_set(source, min_len=3))
    if not src:
        return True
    out = expand_paraphrase_tokens(token_set(summary, min_len=3))
    shared = src & out
    min_shared = 1 if len(source.split()) <= _SHORT_BODY_WORDS else 2
    if len(shared) < min_shared:
        return False
    salient = {t for t in token_set(source, min_len=6) if t not in {"please", "thanks", "merci"}}
    if len(salient) >= 2:
        return len(salient & out) >= 1
    return True


def _body_is_boilerplate(body: str) -> bool:
    lower = body.lower().strip()
    if not lower:
        return True
    boilerplate_markers = (
        "view this message in your browser",
        "manage preferences",
        "unsubscribe",
        "this is an automated response",
    )
    return any(marker in lower for marker in boilerplate_markers)


def _application_rejection_line(body: str, subject: str) -> str | None:
    from voxpost.email_entities import extract_email_entities, is_application_rejection

    if not is_application_rejection(body):
        return None
    entities = extract_email_entities(body, subject=subject)
    if not entities.signatory_name:
        return None
    role = ""
    if entities.application_role:
        role = f" for the {entities.application_role} role"
    if entities.company:
        return f"{entities.signatory_name} from {entities.company} declined your application{role}."
    return f"{entities.signatory_name} declined your job application{role}."


def _intent_hint(body: str, subject: str) -> str | None:
    lower = f"{subject} {body}".lower()
    hints: list[tuple[tuple[str, ...], str]] = [
        (("téléphone", "telephone", "phone number", "numéro", "numero"), "asking for your phone number"),
        (("remboursement", "refund", "charge back", "chargeback"), "requesting a refund"),
        (("paquete", "package", "delivery", "entrega", "llegará"), "about a package delivery"),
        (("réunion", "reunion", "meeting", "gesprek"), "about a meeting change"),
        (("deploy", "migration", "pipeline"), "about a deploy or migration issue"),
        (("invoice", "factura", "due friday", "payment"), "about an invoice or payment"),
        (("sign-in", "sign in", "password", "reset"), "about a sign-in or password reset"),
        (("steuer", "bescheid", "tax", "finanzamt"), "about a tax notice"),
        (("order #", "order#"), "about a missing or delayed order"),
        (("interview", "sollicitatie", "cv"), "about a job interview"),
        (("closed", "snow", "remote learning"), "about a school closure"),
        (("dental", "cleaning", "appointment"), "about a dental appointment"),
        (("pull request", "pr #"), "requesting a code review"),
        ((" code review", "review this pr", "review the pr"), "requesting a code review"),
        (("canceled", "cancelled", "rebook", "flight"), "about a canceled flight"),
        (("rent", "lease", "tenant"), "about a rent or lease change"),
        (("out of the office", "out of office"), "is out of office"),
        (("doc", "document", "get the"), "asking if you got a document"),
    ]
    for keys, phrase in hints:
        if any(k in lower for k in keys):
            return phrase
    return None


def short_fallback_line(event: NewMailEvent, *, normalized_body: str | None = None, lang: str = "en") -> str:
    """Brief template when the model output fails the quality gate (CLI / speech-check)."""
    from voxpost.speakable_fallback import entity_fallback_line, minimal_fallback_line

    entity = entity_fallback_line(event, normalized_body=normalized_body, lang=lang)
    if entity:
        core = entity
    else:
        core = minimal_fallback_line(event, lang=lang)

    words = core.split()
    if len(words) > _FALLBACK_MAX_SPOKEN_WORDS:
        core = " ".join(words[:_FALLBACK_MAX_SPOKEN_WORDS]).rstrip(",;") + "."

    return core if core.endswith(".") else core + "."
