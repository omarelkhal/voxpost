"""Fallback speakable lines when the summarizer output is too weak."""

from __future__ import annotations

import re

from voxpost.events import NewMailEvent

# Model sometimes emits labels with no content on very short/vague mail.
_WEAK_SUMMARIES = frozenset(
    {
        "e-mail:",
        "email:",
        "e-mail",
        "email",
        "message:",
        "subject:",
    }
)

# T5-small may echo instruction-like text when the prompt includes meta tasks.
_META_SUMMARY_MARKERS = (
    "text-to-speech",
    "text to speech",
    "read aloud",
    "cannot see the email",
    "ttstask",
    "fed directly to",
    "write exactly one",
    "spoken sentence",
)

# XLSum news/article bias — common junk on short email bodies.
_CLICKBAIT_MARKERS = (
    "cliquez sur ce lien",
    "click here",
    "click on this link",
    "click this link",
    "read more",
    "lire la suite",
    "full transcript",
    "offshore pipeline",
)

# Chat models fed JSON sometimes echo keys instead of a spoken sentence.
_JSON_ECHO_MARKERS = (
    '"original_sender"',
    '"envelope_from"',
    '"is_forward"',
    '"has_attachments"',
    '"body_truncated"',
)

# Vague intent templates (phone, deploy, …) only for short mail — not event newsletters.
INTENT_FALLBACK_MAX_WORDS = 60


def display_name(from_address: str | None) -> str:
    if not from_address:
        return "Someone"
    text = from_address.strip()
    if "<" in text:
        name = text.split("<", 1)[0].strip().strip('"')
        if name:
            return name
    if "@" in text:
        local = text.split("@", 1)[0]
        return local.replace(".", " ").replace("_", " ").strip() or "Someone"
    return text or "Someone"


_OVERLAP_STOPWORDS = frozenset(
    {
        "your",
        "vous",
        "notre",
        "their",
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "were",
        "will",
        "would",
        "could",
        "should",
        "about",
        "there",
        "where",
        "when",
        "what",
        "which",
        "while",
        "after",
        "before",
        "merci",
        "bonjour",
        "hello",
        "thanks",
        "email",
        "message",
        "subject",
        "omar",
    }
)


def _content_words(text: str, *, min_len: int = 4) -> set[str]:
    words = set(re.findall(rf"\w{{{min_len},}}", text.lower()))
    return words - _OVERLAP_STOPWORDS


def looks_like_json_echo(text: str) -> bool:
    """True when the model returned JSON (or a fragment) instead of plain English."""
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith("{") or stripped.startswith("["):
        return True
    if any(marker in stripped for marker in _JSON_ECHO_MARKERS):
        return True
    # Several `"key":` patterns without being valid prose.
    if stripped.count('"') >= 4 and re.search(r'"\w+"\s*:', stripped):
        return True
    return False


def misattributes_forward(line: str, event: NewMailEvent) -> bool:
    """
    True when a forward was summarized using the envelope sender, not the author.

    Example: envelope Omar, inner Mustafa — reject "Omar wrote, he wants his phone".
    Also rejects naming the forwarder when a signatory (e.g. HR) signed the letter.
    """
    from voxpost.email_clean import clean_email_body, extract_forwarded_sender
    from voxpost.email_entities import extract_email_entities
    from voxpost.summarizer_context import detect_is_forward

    if not detect_is_forward(event):
        return False

    cleaned = clean_email_body(event.body or "")
    entities = extract_email_entities(cleaned, subject=event.subject)
    line_lower = line.lower()

    if entities.signatory_name:
        signatory_first = entities.signatory_name.split()[0].lower()
        envelope = display_name(event.from_address)
        env_first = envelope.split()[0].lower()
        inner = extract_forwarded_sender(event.body or "")
        inner_first = inner.split()[0].lower() if inner and inner.split() else ""
        wrong_names = {n for n in (env_first, inner_first) if len(n) >= 3}
        if wrong_names & set(line_lower.split()) and signatory_first not in line_lower:
            return True
        return False

    original = extract_forwarded_sender(event.body or "")
    if not original:
        return False
    envelope = display_name(event.from_address)
    orig_first = original.split()[0].lower()
    env_first = envelope.split()[0].lower()
    if len(env_first) < 3:
        return False
    if env_first in line_lower and orig_first not in line_lower:
        return True
    return False


def summary_overlaps_source(
    summary: str,
    source: str,
    *,
    chat_lm: bool = False,
    event: NewMailEvent | None = None,
) -> bool:
    """
    Reject XLSum news-style hallucinations on email bodies.

    Chat LMs use a looser paraphrase-aware check (see speakable_gate).
    """
    if chat_lm:
        from voxpost.speakable_gate import summary_overlaps_source_chat

        return summary_overlaps_source_chat(summary, source, event=event)

    src = _content_words(source)
    if not src:
        return True
    out = _content_words(summary)
    shared = src & out
    if len(shared) < 2:
        return False
    salient = _content_words(source, min_len=6)
    if len(salient) >= 2:
        return len(salient & out) >= 1
    return True


def speakable_matches_target_lang(line: str, lang: str) -> bool:
    """Reject speakable lines clearly in the wrong language for TTS config."""
    if not lang or lang == "na":
        return True
    lower = line.lower()
    fr_markers = (
        "annulation",
        "commande",
        "votre",
        "cartes",
        "visite",
        "chiffres",
        "expire",
        "ignorez",
        "demande",
        "origine",
        "confirmation pour",
        "code de",
        "de votre",
        "cet email",
        "n'êtes",
    )
    en_markers = (
        "your",
        "order",
        "cancel",
        "confirmation",
        "verification",
        "declined",
        "application",
        "meeting",
        "invoice",
        "password",
        "wrote",
        "email about",
        "from ",
        " the ",
    )
    fr_hits = sum(1 for m in fr_markers if m in lower)
    en_hits = sum(1 for m in en_markers if m in lower)
    if lang.startswith("en") and fr_hits >= 2 and en_hits == 0:
        return False
    if lang.startswith("fr") and en_hits >= 2 and fr_hits == 0:
        return False
    return True


def is_hard_junk_summary(line: str) -> bool:
    """True when model output is empty or undeniable garbage (not soft quality issues)."""
    text = line.strip()
    if not text:
        return True
    lower = text.lower()
    if lower in _WEAK_SUMMARIES:
        return True
    if looks_like_json_echo(text):
        return True
    if any(marker in lower for marker in _META_SUMMARY_MARKERS):
        return True
    if any(marker in lower for marker in _CLICKBAIT_MARKERS):
        return True
    if "<unused" in lower:
        return True
    if re.search(r"</?[a-z]", text, re.I):
        return True
    if "import re" in lower or "re.sub(" in lower:
        return True
    if "@" in text:
        return True
    if "the sender" in lower:
        return True
    if text.endswith(":") and len(text.split()) <= 2:
        return True
    if len(text) < 12:
        return True
    if len(text.split()) < 3:
        return True
    return False


def is_usable_summary(
    line: str,
    *,
    source: str | None = None,
    event: NewMailEvent | None = None,
    chat_lm: bool = False,
    lang: str | None = None,
) -> bool:
    text = line.strip()
    if is_hard_junk_summary(text):
        return False
    if event and misattributes_forward(text, event):
        return False
    if lang and not speakable_matches_target_lang(text, lang):
        return False
    if source and not summary_overlaps_source(
        text, source, chat_lm=chat_lm, event=event
    ):
        return False
    return True


def entity_fallback_line(
    event: NewMailEvent,
    *,
    normalized_body: str | None = None,
    lang: str = "en",
    body_words: int | None = None,
) -> str | None:
    """High-confidence templates (OTP, rejection) — vague intent only on short mail."""
    from voxpost.email_clean import clean_email_body
    from voxpost.speakable_gate import _application_rejection_line, _intent_hint
    from voxpost.speakable_numbers import verification_code_line

    subject = (event.subject or "").strip()
    subject_clean = re.sub(r"\s+", " ", subject).strip()
    body = normalized_body if normalized_body is not None else clean_email_body(event.body or "")
    body = re.sub(r"\s+", " ", body).strip()
    words = body_words if body_words is not None else len(body.split())

    rejection = _application_rejection_line(body, subject_clean)
    if rejection:
        return rejection
    code_line = verification_code_line(body, subject_clean, lang=lang)
    if code_line:
        return code_line
    if words > INTENT_FALLBACK_MAX_WORDS:
        return None
    hint = _intent_hint(body, subject_clean)
    if hint:
        sender = display_name(event.from_address)
        from voxpost.email_clean import extract_forwarded_sender
        from voxpost.email_entities import extract_email_entities
        from voxpost.summarizer_context import detect_is_forward

        forwarded = extract_forwarded_sender(event.body or "")
        entities = extract_email_entities(body, subject=subject_clean)
        if entities.signatory_name:
            sender = entities.signatory_name
        elif forwarded and subject_clean.lower().startswith(("fwd:", "fw:", "tr:", "re:")):
            sender = forwarded
        elif detect_is_forward(event) and forwarded:
            sender = forwarded
        return f"{sender} {hint}."
    return None


def minimal_fallback_line(event: NewMailEvent, *, lang: str = "en") -> str:
    """Last resort: sender + subject only — no body echo."""
    from voxpost.email_clean import clean_email_body
    from voxpost.speakable_gate import _body_is_boilerplate
    from voxpost.speakable_quality import resolve_author_name

    subject = (event.subject or "").strip()
    subject_clean = re.sub(r"^(?:Fwd|FW|Tr|Re):\s*", "", subject, flags=re.IGNORECASE)
    subject_clean = re.sub(r"\s+", " ", subject_clean).strip()
    body = re.sub(r"\s+", " ", clean_email_body(event.body or "")).strip()
    sender = resolve_author_name(event)

    if _body_is_boilerplate(body) and subject_clean:
        core = f"{sender} emailed about {subject_clean.rstrip('.')}."
    elif subject_clean:
        core = f"{sender} emailed about {subject_clean.rstrip('.')}."
    else:
        core = f"{sender} sent an email."

    if event.has_attachments and event.attachments:
        names = ", ".join(a.filename for a in event.attachments[:2])
        core = core.rstrip(".") + f", with {names} attached."
    return core if core.endswith(".") else core + "."


def fallback_speakable_line(event: NewMailEvent, *, lang: str | None = None) -> str:
    """Template line when the summarizer returns hard junk after retry."""
    from voxpost.user_config import resolved_speakable_lang

    if lang is None:
        lang = resolved_speakable_lang()
    entity = entity_fallback_line(event, lang=lang)
    if entity:
        return entity
    return minimal_fallback_line(event, lang=lang)
