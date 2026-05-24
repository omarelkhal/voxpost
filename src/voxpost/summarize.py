"""Block 3 — local email summarization (mT5 XLSum, no cloud API)."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from voxpost.email_clean import clean_email_body
from voxpost.events import NewMailEvent
from voxpost.speakable_fallback import (
    entity_fallback_line,
    is_hard_junk_summary,
    is_usable_summary,
    minimal_fallback_line,
    speakable_matches_target_lang,
    summary_overlaps_source,
)
from voxpost.speakable_polish import polish_email_text, polish_for_tts
from voxpost.summarized_event import SummarizedMailEvent

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "csebuetnlp/mT5_multilingual_XLSum"

# Model card defaults for csebuetnlp/mT5_multilingual_XLSum
MAX_INPUT_TOKENS = 512
MAX_NEW_TOKENS = 84
NUM_BEAMS = 4
NO_REPEAT_NGRAM_SIZE = 2
MAX_BODY_CHARS = 1800

FLAN_MAX_NEW_TOKENS = 36

CHAT_LM_MAX_NEW_TOKENS = 96

# Body length tiers for speakable-line detail (word counts on normalized body).
SHORT_MAIL_WORDS = 50
LONG_MAIL_WORDS = 120
INTENT_FALLBACK_MAX_WORDS = 60
# English briefing of French mail shares few tokens — keep substantive target-lang lines.
MIN_CROSS_LANG_SUMMARY_WORDS = 12

def _output_language_lock(lang: str) -> str:
    """Hard requirement: speakable output uses TOML config language, never the email language."""
    code = (lang or "en").strip().lower()
    return (
        f"Output language: {code} only. "
        "Translate from any source language (French, Spanish, German, Italian, "
        "Dutch, Portuguese, Japanese, mixed). "
        f"Never reply in the email's language — always use {code} from the user config."
    )


# Shared output contract for chat-LM and FLAN instruction prefixes.
_SPEAKABLE_CONTRACT_CORE = """\
You are Voxpost, a voice assistant. For each incoming email, write ONE spoken \
briefing for a listener who cannot see the screen and has NOT read the email \
yet. Speak as the assistant, naturally, as if telling a colleague what just \
arrived — never as if they already saw it.

OUTPUT FORMAT
- One block of plain spoken prose. No JSON, no labels, no bullet points, no \
markdown, no headings, no quotes around the line.
- No preamble: never start with "Here is", "Here's", "Summary:", "Briefing:", \
"Sure,", "Of course,", "The email says".
- No reasoning, no thinking trace blocks, no "Thinking:", no "Let me", no "Step 1", \
no meta narration. Output the briefing only, then stop.
- Never include email addresses, the "@" symbol, URLs, or raw header lines.

CLASSIFY FIRST — exactly one of two:

(A) SPAM — ONLY if ALL THREE are true:
   1. Sender is a brand, store, mailing list, or automated marketing system \
(not a real person, not a service the listener uses, not a forward).
   2. Body is selling, promoting, discounting, or pushing a signup / newsletter / CTA.
   3. There is no specific personal fact, action, or deadline the listener owns.
   Pattern: "You received an email about <concrete marketing topic>. \
Worth checking — it might be spam." — summary first, soft hedge last. \
Never say "This looks like spam" or "This is spam"; you are not sure.

(B) IMPORTANT — everything else. Default to IMPORTANT when in doubt.

These are ALWAYS IMPORTANT — never label them spam:
- Security alerts, sign-in notices, password resets, suspicious-activity warnings.
- Forwarded personal mail (a real human is behind the Gmail forwarder).
- Booking, delivery, invoice, tax, official, legal, government, school notices.
- Interview, appointment, calendar move, reservation confirmation.
- Customer complaints, including ALL-CAPS or angry tone.
- Internal team messages, deploy or CI alerts, code review, GitHub pull requests.
- Out-of-office auto-replies — state them factually as info.
- Subject-only or one-line pings from a real person.
Tie-breaker: if you cannot name a real marketing topic after "You received an \
email about", it is NOT spam.

FOR IMPORTANT MAIL, INCLUDE:
- Open as a fresh arrival: "You received an email from …", "Security alert …", \
"Forwarded from …", or similar — never "This looks like".
- Who it is from. For forwards, name the ORIGINAL sender or their role \
("your client Marc Dubois", "your landlord", "the airline"), never the Gmail \
forwarder. Use the signatory or the in-body "From:" line.
- What happened or what is being asked.
- Any concrete date, time, deadline, place, amount, document, code, or action.
- The required next step, said calmly as a suggestion, not as a command.
When a signatory name and company appear at the end (HR letters, rejections), \
name that person and company — not the forwarder. Include the job or role from \
the subject when it is an application update.

PRESERVE FACTS
- Keep a.m. / p.m. exactly as the email states them. Never flip 4 p.m. to 4 a.m.
- Never invent names, dates, times, amounts, urgency, or actions.
- If a fact is missing, omit it — do not guess.

BANNED PHRASES — never emit:
- "This looks like spam", "This is spam", "Definitely spam", or any firm spam \
verdict — you are never sure; hedge only.
- Starting with "This looks like" — the listener has not seen the mail.
- "the sender", "this sender", "the email", "the message", "in this email".
- "sent a message saying", "sent an email about", "writes that", \
"wants to inform you", "is reaching out".
- "about booking", "about meeting", "about a sign-in" — be concrete instead.
- "you should buy", "great deal for you", any promotional CTA echo on non-spam.
- Spam template on important mail (security, school, forward, complaint, \
invoice, interview, OOO, deploy, PR) — these are always wrong.

EXAMPLES

[1] Newsletter spam (the only allowed spam shape)
From: deals@store.example
Subject: 50% OFF EVERYTHING THIS WEEKEND
Body: Don't miss our biggest sale of the year. Shop now.
→ You received an email about a fifty percent off weekend sale. \
Worth checking — it might be spam.

[2] Security alert (never spam, even though automated)
From: security@accounts.example
Subject: New sign-in from Berlin
Body: We noticed a sign-in to your account from Berlin at 02:14 UTC. \
If this wasn't you, reset your password.
→ Security alert: someone signed in to your account from Berlin at two \
fourteen a.m. UTC — reset your password if that wasn't you.

[3] Forwarded French client mail (name the original sender, translate)
From: assistant@yourdomain.com
Subject: Fwd: petite question
Body: ---------- Forwarded message ---------- From: Marc Dubois \
<marc@client.fr> Bonjour, peux-tu m'envoyer ton numéro de téléphone ? Merci, Marc
→ Forwarded from your client Marc Dubois — he is asking you to send him your \
phone number.

[4] Dutch interview invite (translate date and place; never spam)
From: hr@company.nl
Subject: Uitnodiging sollicitatiegesprek
Body: Wij willen u uitnodigen voor een gesprek op woensdag 15 mei om 14:00 \
op kantoor in Amsterdam.
→ Job interview invitation — Wednesday May fifteenth at two p.m. at the \
company's Amsterdam office.

[5] Angry ALL-CAPS customer (never spam; order number digit by digit)
From: angry@buyer.example
Subject: WHERE IS MY ORDER
Body: ORDER 99281 STILL NOT SHIPPED. I DEMAND A CALLBACK TODAY.
→ An angry customer is complaining that order nine nine two eight one still \
hasn't shipped and is demanding a callback today.
"""

_LENGTH_GUIDANCE = """\
LENGTH — adapt to the email body word count:
- ≤ 50 words → one short sentence.
- 51 to 120 words → one or two sentences.
- > 120 words → as many short sentences as needed; never drop dates, times, \
deadlines, venues, amounts, document names, or limits.
Do not artificially shorten long mail.
"""

_CHAT_USER_FOOTER = (
    "Write the spoken briefing for this email now. "
    "Output the briefing only, on a single block, then stop."
)

_CHAT_USER_STRUCTURED_RULES = """\
Rules for the structured fields:
- If is_forward is true, name original_sender or signatory_name in the \
briefing, never envelope_from.
- If signatory_name is present, prefer it over envelope_from.
- If application_role is present, the email is about a job application — say the role.
- attachments lists filename and mime type only; mention a document by name if \
relevant ("the invoice PDF", "the contract attached"), never attachment body content.
"""

_BRIEFING_PREAMBLE_RE = re.compile(
    r"^(?:here(?:'s| is)(?: the)?(?: spoken)?(?: briefing)?\s*[:\-]?\s*|"
    r"sure[,!]?\s*|of course[,!]?\s*|briefing\s*[:\-]\s*|"
    r"summary\s*[:\-]\s*)",
    re.IGNORECASE,
)

_CHAT_BRIEFING_STOP_MARKERS = (
    "\n\n",
    "Thinking:",
    "Reasoning:",
    "Note:",
    "Explanation:",
    "Here is",
    "Here's",
)


def _tts_speech_rules(lang: str) -> str:
    code = (lang or "en").strip().lower()
    if code.startswith("fr"):
        return (
            "TTS NUMBER RULES — every number as spoken words, never digits: "
            "codes OTP chiffre par chiffre; montants en toutes lettres avec l'unité monétaire; "
            "heures en toutes lettres pour la synthèse vocale. "
            f"Always reply in {code} only — the configured output language from "
            "voxpost.toml, never the email language."
        )
    return (
        "TTS NUMBER RULES — every number as spoken words, never digits:\n"
        '- Times spoken naturally: "three p.m.", "nine forty-five a.m.", '
        '"two fourteen a.m. UTC".\n'
        '- Money in full words with currency: "two hundred fifty euros", '
        '"one thousand two hundred dollars".\n'
        '- OTP, verification, tracking, invoice, order, phone numbers: digit by digit '
        '("four four two one", "nine nine two eight one").\n'
        '- Dates spoken naturally: "Thursday the twelfth", "March third", '
        '"April fifteenth".\n'
        '- Percentages as words: "fifty percent".\n'
        f"Always reply in {code} only — the configured output language from "
        "voxpost.toml, never the email language."
    )


def _chat_length_guidance(body_words: int) -> str:
    """Legacy hook for FLAN; chat-LM system prompt uses static _LENGTH_GUIDANCE."""
    if body_words <= SHORT_MAIL_WORDS:
        return " Reply with one short sentence."
    if body_words <= LONG_MAIL_WORDS:
        return " Reply with one or two sentences."
    return " Reply with as many short sentences as needed; do not drop key facts."


def _chat_system_prompt(*, structured: bool, lang: str, body_words: int = 0) -> str:
    del structured, body_words  # same system contract for plain and structured
    code = (lang or "en").strip().lower()
    return "\n\n".join(
        [
            _output_language_lock(code),
            _SPEAKABLE_CONTRACT_CORE,
            _LENGTH_GUIDANCE,
            _tts_speech_rules(code),
        ]
    )


def format_chat_user_message(email_text: str, *, structured: bool) -> str:
    """User turn for chat-LM summarization (plain email context or structured JSON)."""
    if structured:
        return (
            "EMAIL (structured fields — use them, do not echo them)\n"
            f"{email_text}\n\n"
            f"{_CHAT_USER_STRUCTURED_RULES}\n\n"
            f"{_CHAT_USER_FOOTER}"
        )
    return f"EMAIL\n{email_text}\n\n{_CHAT_USER_FOOTER}"


# Kept for imports / backwards compatibility; chat path uses format_chat_user_message.
CHAT_LM_SYSTEM_PROMPT = _SPEAKABLE_CONTRACT_CORE
CHAT_LM_SYSTEM_PROMPT_STRUCTURED = _SPEAKABLE_CONTRACT_CORE

VALID_CHAT_INPUT_FORMATS = frozenset({"plain", "structured"})


def _uses_t5gemma2(model_id: str) -> bool:
    """Google T5Gemma 2 encoder-decoder (multimodal processor, text-only OK)."""
    normalized = model_id.lower().replace("\\", "/")
    return "t5gemma-2" in normalized or "t5gemma2" in normalized


def _uses_flan_prompt(model_id: str) -> bool:
    normalized = model_id.lower().replace("\\", "/")
    return "flan-t5" in normalized or "flan_t5" in normalized


def _uses_causal_chat(model_id: str) -> bool:
    """Instruction-tuned causal LMs (Qwen, SmolLM2, Phi, …) with chat templates."""
    normalized = model_id.lower().replace("\\", "/")
    return (
        "qwen" in normalized
        or "smollm" in normalized
        or "phi-" in normalized
        or "phi4" in normalized
    )


def _is_qwen35(model_id: str) -> bool:
    normalized = model_id.lower().replace("\\", "/")
    return "qwen3.5" in normalized or "qwen3_5" in normalized


def _uses_email_context(model_id: str) -> bool:
    return _uses_flan_prompt(model_id) or _uses_causal_chat(model_id)


def _strip_thinking_blocks(text: str) -> str:
    """Remove Qwen-style thinking segments from model output."""
    cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return cleaned.strip()


def _truncate_at_stop_markers(text: str) -> str:
    line = text.strip()
    for marker in _CHAT_BRIEFING_STOP_MARKERS:
        idx = line.find(marker)
        if idx > 0:
            line = line[:idx].strip()
    return line


def _clean_chat_briefing(text: str) -> str:
    """Post-process chat-LM briefing: strip thinking, preambles, extra paragraphs."""
    line = _truncate_at_stop_markers(_strip_thinking_blocks(text.strip()))
    line = _BRIEFING_PREAMBLE_RE.sub("", line).strip().strip('"').strip("'")
    return re.sub(r"\s+", " ", line).strip()


def _seq2seq_speakable_prefix(lang: str) -> str:
    """Instruction prefix for mT5/XLSum seq2seq models (no chat template)."""
    code = (lang or "en").strip().lower()
    return (
        f"Write a spoken assistant briefing in {code} only — "
        f"the configured output language, never the email language. "
    )


def _t5gemma2_task_prefix(*, lang: str = "en") -> str:
    """UL2-style task prefix for pretrained T5Gemma 2 (not instruction-tuned)."""
    code = (lang or "en").strip().lower()
    return f"summarize in {code}: "


def _flan_prompt(body_words: int = 0, *, lang: str = "en") -> str:
    if body_words <= SHORT_MAIL_WORDS:
        length = (
            "Write one brief sentence: what the user needs to hear — spam, request, "
            "confirmation, reminder, or alert."
        )
    elif body_words <= LONG_MAIL_WORDS:
        length = (
            "Write one or two sentences for text-to-speech: what happened and why it "
            "matters, true author if useful, and any date, time, place, deadline, or action."
        )
    else:
        length = (
            "Write as many short sentences as needed for text-to-speech: what happened, "
            "why it matters, what to do, true author, when and where if relevant, and any "
            "limits or deadlines. Do not omit dates, times, venues, or constraints."
        )
    return (
        f"{_output_language_lock(lang)}"
        f"Create a spoken assistant briefing for this email. {_SPEAKABLE_CONTRACT_CORE} "
        f"{length}{_tts_speech_rules(lang)}\n"
    )


def wrap_model_input(
    model_input: str,
    *,
    model_id: str,
    body_words: int = 0,
    lang: str = "en",
) -> str:
    """Instruction-tuned models (FLAN-T5) need a task prefix; XLSum expects raw text."""
    if model_id and _uses_t5gemma2(model_id):
        return _t5gemma2_task_prefix(lang=lang) + model_input
    if _uses_flan_prompt(model_id):
        return _flan_prompt(body_words, lang=lang) + model_input
    if not _uses_causal_chat(model_id):
        return _seq2seq_speakable_prefix(lang) + model_input
    return model_input


def _load_summarize_config(config_dir: Path | None):
    from voxpost.user_config import load_user_config

    return load_user_config(config_dir).summarize


def resolved_summarize_backend(config_dir: Path | None = None) -> str:
    """``transformers`` (default) or ``ollama``."""
    return _load_summarize_config(config_dir).backend.lower()


def _uses_chat_mail_input(model_id: str, *, backend: str) -> bool:
    return backend == "ollama" or _uses_causal_chat(model_id)


def _resolved_cpu_threads(config) -> int:
    """Cap PyTorch CPU threads; 0 means half of logical cores (min 1)."""
    if config.cpu_threads > 0:
        return config.cpu_threads
    count = os.cpu_count() or 4
    return max(1, count // 2)


def _torch_backend_available(name: str) -> bool:
    import torch

    if name == "cuda":
        return hasattr(torch, "cuda") and torch.cuda.is_available()
    if name == "mps":
        return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    return name == "cpu"


def resolved_torch_device(device: str = "auto") -> str:
    """
    Resolve ``auto`` | ``cpu`` | ``cuda`` | ``gpu`` | ``mps`` to a torch device string.

    ``auto`` prefers CUDA, then Apple MPS, then CPU.
    """
    choice = device.strip().lower()
    if choice == "gpu":
        choice = "cuda"
    if choice == "auto":
        if _torch_backend_available("cuda"):
            return "cuda"
        if _torch_backend_available("mps"):
            return "mps"
        return "cpu"
    if choice not in {"cpu", "cuda", "mps"}:
        raise ValueError(f"unsupported torch device {device!r}")
    if choice != "cpu" and not _torch_backend_available(choice):
        logger.warning(
            "Requested summarizer device %r is unavailable; falling back to CPU",
            choice,
        )
        return "cpu"
    return choice


def _move_model_to_device(model: Any, device: str) -> Any:
    if device == "cpu":
        return model
    return model.to(device)


def _encode_on_device(tokenizer, text: str, *, device: str) -> dict[str, Any]:
    encoded = tokenizer(
        text,
        return_tensors="pt",
        max_length=MAX_INPUT_TOKENS,
        truncation=True,
    )
    if device == "cpu":
        return encoded
    return {key: value.to(device) for key, value in encoded.items()}


def _move_tensor_dict_to_device(encoded: dict[str, Any], device: str) -> dict[str, Any]:
    if device == "cpu":
        return encoded
    moved: dict[str, Any] = {}
    for key, value in encoded.items():
        if hasattr(value, "to"):
            moved[key] = value.to(device)
        else:
            moved[key] = value
    return moved


def _processor_encode_on_device(processor, text: str, *, device: str) -> dict[str, Any]:
    encoded = processor(
        text=text,
        return_tensors="pt",
        max_length=MAX_INPUT_TOKENS,
        truncation=True,
    )
    return _move_tensor_dict_to_device(encoded, device)


def _apply_torch_threads(threads: int) -> None:
    import torch

    torch.set_num_threads(threads)
    interop = min(2, threads)
    try:
        torch.set_num_interop_threads(interop)
    except RuntimeError:
        pass


def _resolve_torch_dtype(load_dtype: str, *, causal_chat: bool, device: str = "cpu"):
    import torch

    choice = load_dtype.lower()
    if choice == "auto":
        if device in {"cuda", "mps"}:
            return torch.float16
        return torch.float16 if causal_chat else None
    mapping = {
        "float16": torch.float16,
        "float32": torch.float32,
        "bfloat16": torch.bfloat16,
    }
    return mapping[choice]


def _seq2seq_max_new_tokens(body_words: int) -> int:
    if body_words <= SHORT_MAIL_WORDS:
        return MAX_NEW_TOKENS
    if body_words <= LONG_MAIL_WORDS:
        return max(MAX_NEW_TOKENS, 120)
    return max(MAX_NEW_TOKENS, 160)


def _flan_max_new_tokens(body_words: int) -> int:
    if body_words <= SHORT_MAIL_WORDS:
        return FLAN_MAX_NEW_TOKENS
    if body_words <= LONG_MAIL_WORDS:
        return max(FLAN_MAX_NEW_TOKENS, 64)
    return max(FLAN_MAX_NEW_TOKENS, 96)


def _chat_max_new_tokens(config_dir: Path | None, *, body_words: int = 0) -> int:
    base = _load_summarize_config(config_dir).chat_max_new_tokens
    if body_words <= SHORT_MAIL_WORDS:
        return base
    if body_words <= LONG_MAIL_WORDS:
        return max(base, 96)
    return max(base, 128)


def resolved_model_id(config_dir: Path | None = None) -> str:
    """Env → voxpost.toml [summarize].model → built-in default."""
    env = os.environ.get("VOXPOST_SUMMARIZER_MODEL")
    if env and env.strip():
        return env.strip()
    from voxpost.user_config import load_user_config

    return load_user_config(config_dir).summarize.model


def model_cache_dir(config_dir: Path, model: str | None = None) -> Path:
    override = os.environ.get("VOXPOST_MODEL_DIR")
    if override:
        return Path(os.path.expanduser(override)).resolve()
    target = model or resolved_model_id(config_dir)
    folder = Path(target.replace("\\", "/")).name
    return config_dir / "models" / folder


def _normalize_body(event: NewMailEvent) -> str:
    body = clean_email_body(event.body or "")
    body = polish_email_text(body)
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS].rstrip() + "…"
    return body


def _email_context(event: NewMailEvent, body: str) -> str:
    """From + subject + body + extracted signatory/company for chat LMs."""
    from voxpost.summarizer_context import build_summarizer_context

    ctx = build_summarizer_context(event, normalized_body=body)
    subject = ctx.subject or ""
    skip_subj = subject.lower().rstrip(":") in {"fwd", "fw", "re", ""}
    lines: list[str] = []
    if ctx.signatory_name:
        sig = ctx.signatory_name
        if ctx.signatory_title:
            sig = f"{sig}, {ctx.signatory_title}"
        lines.append(f"Signatory: {sig}")
    elif ctx.envelope_from:
        lines.append(f"From: {ctx.envelope_from}")
    if ctx.company:
        lines.append(f"Company: {ctx.company}")
    if ctx.application_role:
        lines.append(f"Role: {ctx.application_role}")
    if subject and not skip_subj:
        lines.append(f"Subject: {subject}")
    lines.append(body if body else "(empty body)")
    return "\n".join(lines)


def _structured_model_input(event: NewMailEvent, body: str) -> str:
    from voxpost.summarizer_context import (
        body_was_truncated,
        build_summarizer_context,
    )

    truncated = body_was_truncated(event, body, max_chars=MAX_BODY_CHARS)
    ctx = build_summarizer_context(
        event,
        normalized_body=body,
        body_truncated=truncated,
    )
    return ctx.to_json()


def resolved_chat_input_format(config_dir: Path | None = None) -> str:
    """plain (From/Subject/Body) or structured (JSON) for chat LMs."""
    env = os.environ.get("VOXPOST_SUMMARIZER_INPUT")
    if env and env.strip().lower() in VALID_CHAT_INPUT_FORMATS:
        return env.strip().lower()
    fmt = _load_summarize_config(config_dir).chat_input_format.lower()
    if fmt not in VALID_CHAT_INPUT_FORMATS:
        return "plain"
    return fmt


def build_model_input(
    event: NewMailEvent,
    *,
    model_id: str | None = None,
    input_format: str | None = None,
) -> str:
    """
    Format a NewMailEvent for the summarizer.

    XLSum expects plain body text. FLAN gets From/Subject/Body. Chat LMs may use
    plain lines or structured JSON (input_format / VOXPOST_SUMMARIZER_INPUT).
    """
    body = _normalize_body(event)
    if model_id and _uses_causal_chat(model_id):
        fmt = (input_format or "plain").lower()
        if fmt == "structured":
            return _structured_model_input(event, body)
        if body:
            return _email_context(event, body)
        subject = polish_email_text((event.subject or "").strip())
        if subject and subject.lower().rstrip(":") not in {"fwd", "fw", "re", ""}:
            return _email_context(event, subject)
        return _email_context(event, "")

    if model_id and _uses_flan_prompt(model_id):
        if body:
            return _email_context(event, body)
        subject = polish_email_text((event.subject or "").strip())
        if subject and subject.lower().rstrip(":") not in {"fwd", "fw", "re", ""}:
            return _email_context(event, subject)
        return _email_context(event, "")

    if model_id and _uses_t5gemma2(model_id):
        if body:
            return body
        subject = polish_email_text((event.subject or "").strip())
        if subject and subject.lower().rstrip(":") not in {"fwd", "fw", "re", ""}:
            return subject
        return "(empty)"

    if body:
        return body
    subject = polish_email_text((event.subject or "").strip())
    if subject and subject.lower().rstrip(":") not in {"fwd", "fw", "re", ""}:
        return subject
    return "(empty)"


def sample_mail_event() -> NewMailEvent:
    """Representative event for offline CLI tests."""
    from voxpost.attachments import AttachmentInfo

    return NewMailEvent(
        account_id="user@example.com",
        message_id="sample-msg-001",
        thread_id="sample-thread",
        history_id="12345",
        received_at="Thu, 21 May 2026 10:00:00 +0000",
        from_address="Alex Chen <alex@company.com>",
        subject="Staging deploy failed",
        body=(
            "Hey — the staging deploy failed around 9:45. "
            "Looks like the migration step timed out. "
            "Can you check the pipeline logs when you get a chance? "
            "I attached the error snippet."
        ),
        has_attachments=True,
        attachment_count=1,
        attachments=(
            AttachmentInfo(
                filename="error.log",
                mime_type="text/plain",
                size_bytes=4096,
            ),
        ),
    )


class EmailSummarizer:
    """Lazy-loaded local summarizer. Requires optional `summarize` extras."""

    def __init__(
        self,
        model: str | None = None,
        *,
        config_dir: Path | None = None,
        local_files_only: bool = False,
        speakable_lang: str | None = None,
    ) -> None:
        self._config_dir = config_dir
        self._model_id = model or resolved_model_id(config_dir)
        self._local_files_only = local_files_only
        self._speakable_lang_override = (
            speakable_lang.strip().lower() if speakable_lang else None
        )
        self._pipe: Any = None
        self._backend: str | None = None
        self._torch_device: str = "cpu"

    @property
    def speakable_lang(self) -> str:
        """Spoken output language (CLI override or TOML speech/tts settings)."""
        if self._speakable_lang_override:
            return self._speakable_lang_override
        from voxpost.user_config import resolved_speakable_lang

        return resolved_speakable_lang(self._config_dir)

    @property
    def model_id(self) -> str:
        return self._model_id

    def _resolve_model_ref(self) -> str:
        if self._config_dir is not None:
            local = model_cache_dir(self._config_dir, self._model_id)
            if (local / "config.json").exists():
                return str(local)
        return self._model_id

    def _summarize_backend(self) -> str:
        return resolved_summarize_backend(self._config_dir)

    def _ensure_ollama(self) -> None:
        if self._backend == "ollama":
            return
        sum_cfg = _load_summarize_config(self._config_dir)
        from voxpost.ollama_client import ollama_model_available

        if not ollama_model_available(sum_cfg.ollama_host, self._model_id):
            raise RuntimeError(
                f"Ollama model {self._model_id!r} not found at {sum_cfg.ollama_host}. "
                f"Run: ollama pull {self._model_id}"
            )
        logger.info(
            "Using Ollama summarizer %s at %s",
            self._model_id,
            sum_cfg.ollama_host,
        )
        self._backend = "ollama"
        self._pipe = True

    def _ensure_loaded(self) -> None:
        if self._summarize_backend() == "ollama":
            self._ensure_ollama()
            return
        if self._pipe is not None:
            return
        try:
            from transformers import AutoTokenizer
        except ImportError as err:
            raise RuntimeError(
                "Summarization requires optional dependencies. Install with:\n"
                "  pip install 'voxpost[summarize]'"
            ) from err

        sum_cfg = _load_summarize_config(self._config_dir)
        self._torch_device = resolved_torch_device(sum_cfg.device)
        if self._torch_device == "cpu":
            _apply_torch_threads(_resolved_cpu_threads(sum_cfg))

        model_ref = self._resolve_model_ref()
        logger.info(
            "Loading summarizer model %s (%s)",
            model_ref,
            self._torch_device.upper(),
        )
        load_kwargs: dict[str, Any] = {"low_cpu_mem_usage": True}
        if self._local_files_only:
            load_kwargs["local_files_only"] = True

        causal_chat = _uses_causal_chat(self._model_id)
        dtype = _resolve_torch_dtype(
            sum_cfg.load_dtype,
            causal_chat=causal_chat,
            device=self._torch_device,
        )
        if dtype is not None:
            load_kwargs["dtype"] = dtype

        if _uses_t5gemma2(self._model_id):
            from transformers import AutoModelForSeq2SeqLM, AutoProcessor

            proc_kwargs = {k: v for k, v in load_kwargs.items() if k != "dtype"}
            try:
                processor = AutoProcessor.from_pretrained(model_ref, **proc_kwargs)
            except (ImportError, OSError) as exc:
                msg = str(exc).lower()
                if "torchvision" in msg or "gemma3imageprocessor" in msg:
                    raise RuntimeError(
                        "T5Gemma 2 requires torchvision for its processor. "
                        "Install summarize extras: pip install voxpost[summarize]"
                    ) from exc
                raise
            seq_model = AutoModelForSeq2SeqLM.from_pretrained(model_ref, **load_kwargs)
            seq_model = _move_model_to_device(seq_model, self._torch_device)
            seq_model.eval()
            self._backend = "t5gemma2"
            self._pipe = (processor, seq_model)
            return

        tokenizer = AutoTokenizer.from_pretrained(model_ref, **load_kwargs)

        if causal_chat:
            from transformers import AutoModelForCausalLM

            model = AutoModelForCausalLM.from_pretrained(model_ref, **load_kwargs)
            model = _move_model_to_device(model, self._torch_device)
            model.eval()
            self._backend = "chat"
            self._pipe = (tokenizer, model)
            return

        from transformers import AutoModelForSeq2SeqLM

        seq_model = AutoModelForSeq2SeqLM.from_pretrained(model_ref, **load_kwargs)
        seq_model = _move_model_to_device(seq_model, self._torch_device)
        seq_model.eval()
        self._backend = "seq2seq"
        self._pipe = (tokenizer, seq_model)

    def unload(self) -> None:
        """Drop loaded weights and encourage the runtime to release RAM."""
        if self._pipe is None:
            return
        if self._backend == "ollama":
            logger.info("Releasing Ollama summarizer session for %s", self._model_id)
            self._pipe = None
            self._backend = None
            return
        logger.info("Unloading summarizer model %s", self._model_id)
        self._pipe = None
        self._backend = None
        self._torch_device = "cpu"
        import gc

        gc.collect()
        try:
            import torch

            if hasattr(torch, "cuda") and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def _summarize_chat(self, email_text: str, *, structured: bool = False, body_words: int = 0) -> str:
        self._ensure_loaded()
        assert self._pipe is not None
        tokenizer, model = self._pipe
        import torch

        system = _chat_system_prompt(
            structured=structured,
            lang=self.speakable_lang,
            body_words=body_words,
        )
        user_content = format_chat_user_message(email_text, structured=structured)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        template_kwargs: dict[str, Any] = {}
        if _is_qwen35(self._model_id):
            template_kwargs["enable_thinking"] = False
        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                **template_kwargs,
            )
        except TypeError:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        encoded = _encode_on_device(
            tokenizer,
            prompt,
            device=self._torch_device,
        )
        input_len = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            output_ids = model.generate(
                **encoded,
                max_new_tokens=_chat_max_new_tokens(self._config_dir, body_words=body_words),
                do_sample=False,
                repetition_penalty=1.05,
            )
        new_ids = output_ids[0, input_len:]
        line = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        return _clean_chat_briefing(line)

    def _summarize_ollama(
        self,
        email_text: str,
        *,
        structured: bool = False,
        body_words: int = 0,
    ) -> str:
        from voxpost.ollama_client import ollama_chat

        self._ensure_ollama()
        sum_cfg = _load_summarize_config(self._config_dir)
        system = _chat_system_prompt(
            structured=structured,
            lang=self.speakable_lang,
            body_words=body_words,
        )
        user_content = format_chat_user_message(email_text, structured=structured)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        line = ollama_chat(
            host=sum_cfg.ollama_host,
            model=self._model_id,
            messages=messages,
            max_tokens=_chat_max_new_tokens(self._config_dir, body_words=body_words),
        )
        return _clean_chat_briefing(line)

    def summarize_event_text(
        self,
        event: NewMailEvent,
        *,
        input_format: str | None = None,
    ) -> str:
        """Return raw model output for one mail event (review / pipeline entry)."""
        fmt = input_format or resolved_chat_input_format(self._config_dir)
        body_words = len(_normalize_body(event).split())
        backend = self._summarize_backend()
        email_text = build_model_input(
            event,
            model_id=self._model_id,
            input_format=fmt if _uses_chat_mail_input(self._model_id, backend=backend) else None,
        )
        if backend == "ollama":
            raw = self._summarize_ollama(
                email_text,
                structured=(fmt == "structured"),
                body_words=body_words,
            )
        elif _uses_causal_chat(self._model_id):
            raw = self._summarize_chat(
                email_text,
                structured=(fmt == "structured"),
                body_words=body_words,
            )
        else:
            raw = self.summarize_text(email_text, body_words=body_words)
        return self._adjust_spam_template(raw, event)

    def _adjust_spam_template(self, line: str, event: NewMailEvent) -> str:
        from voxpost.speakable_gate import adjust_misapplied_spam_template

        return adjust_misapplied_spam_template(
            line,
            event,
            normalized_body=_normalize_body(event),
        )

    def summarize_text(self, model_input: str, *, body_words: int = 0) -> str:
        self._ensure_loaded()
        assert self._pipe is not None
        import torch

        model_input = wrap_model_input(
            model_input,
            model_id=self._model_id,
            body_words=body_words,
            lang=self.speakable_lang,
        )
        if _uses_flan_prompt(self._model_id):
            max_tokens = _flan_max_new_tokens(body_words)
            beams = NUM_BEAMS
        elif self._backend == "t5gemma2":
            max_tokens = _seq2seq_max_new_tokens(body_words)
            beams = 2
        else:
            max_tokens = _seq2seq_max_new_tokens(body_words)
            beams = NUM_BEAMS
        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": max_tokens,
            "num_beams": beams,
            "no_repeat_ngram_size": NO_REPEAT_NGRAM_SIZE,
            "do_sample": False,
        }

        if self._backend == "t5gemma2":
            processor, seq_model = self._pipe
            encoded = _processor_encode_on_device(
                processor,
                model_input,
                device=self._torch_device,
            )
            with torch.inference_mode():
                output_ids = seq_model.generate(**encoded, **gen_kwargs)
            line = processor.decode(output_ids[0], skip_special_tokens=True).strip()
            return re.sub(r"\s+", " ", line).strip()

        tokenizer, seq_model = self._pipe
        encoded = _encode_on_device(
            tokenizer,
            model_input,
            device=self._torch_device,
        )
        with torch.inference_mode():
            output_ids = seq_model.generate(**encoded, **gen_kwargs)
        line = tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        return re.sub(r"\s+", " ", line).strip()

    def summarize_event(self, event: NewMailEvent) -> SummarizedMailEvent:
        source_body = _normalize_body(event)
        body_words = len(source_body.split())
        speak_lang = self.speakable_lang
        chat_lm = _uses_chat_mail_input(
            self._model_id,
            backend=self._summarize_backend(),
        )

        line = polish_for_tts(self.summarize_event_text(event), lang=speak_lang)

        if is_hard_junk_summary(line):
            logger.info("Summarizer returned junk %r; retrying once", line)
            retry = polish_for_tts(self.summarize_event_text(event), lang=speak_lang)
            if not is_hard_junk_summary(retry):
                line = retry
            else:
                logger.info(
                    "Summarizer retry still junk %r; using entity or subject fallback",
                    retry,
                )
                entity = entity_fallback_line(
                    event, lang=speak_lang, body_words=body_words
                )
                line = polish_for_tts(
                    entity or minimal_fallback_line(event, lang=speak_lang),
                    lang=speak_lang,
                )
        elif not is_usable_summary(
            line,
            source=source_body,
            event=event,
            chat_lm=chat_lm,
            lang=speak_lang,
        ):
            entity = entity_fallback_line(event, lang=speak_lang, body_words=body_words)
            if entity:
                logger.info("Entity fallback after quality gate (was %r)", line)
                line = polish_for_tts(entity, lang=speak_lang)
            elif body_words > LONG_MAIL_WORDS:
                logger.info(
                    "Keeping long-mail summarizer line despite quality gate: %r",
                    line,
                )
            elif not summary_overlaps_source(
                line,
                source_body,
                chat_lm=chat_lm,
                event=event,
            ):
                if (
                    speak_lang
                    and speakable_matches_target_lang(line, speak_lang)
                    and len(line.split()) >= MIN_CROSS_LANG_SUMMARY_WORDS
                ):
                    logger.info(
                        "Keeping target-lang summarizer line despite overlap gate: %r",
                        line,
                    )
                else:
                    logger.info(
                        "Subject fallback after hallucination (was %r)",
                        line,
                    )
                    line = polish_for_tts(
                        minimal_fallback_line(event, lang=speak_lang),
                        lang=speak_lang,
                    )
            else:
                logger.info(
                    "Keeping summarizer line despite soft quality gate: %r",
                    line,
                )

        return SummarizedMailEvent.from_mail_event(event, line)

def download_summarizer_model(
    config_dir: Path,
    model: str | None = None,
) -> Path:
    """
    Download model weights into the Hugging Face cache (and verify load path).

    For ``backend = ollama``, pulls via the local Ollama daemon instead.

    Returns the snapshot directory path.
    """
    sum_cfg = _load_summarize_config(config_dir)
    target = model or resolved_model_id(config_dir)

    if sum_cfg.backend == "ollama":
        from voxpost.ollama_client import ollama_pull

        logger.info("Pulling Ollama model %s …", target)
        ollama_pull(sum_cfg.ollama_host, target)
        return Path(f"ollama:{target}")

    try:
        from huggingface_hub import snapshot_download
    except ImportError as err:
        raise RuntimeError(
            "Model download requires optional dependencies. Install with:\n"
            "  pip install 'voxpost[summarize]'"
        ) from err

    target = model or resolved_model_id(config_dir)
    cache = model_cache_dir(config_dir, target)
    cache.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading %s …", target)
    path = snapshot_download(
        repo_id=target,
        cache_dir=str(cache.parent),
        local_dir=str(cache),
    )
    return Path(path)


def summarize_mail_event(
    event: NewMailEvent,
    *,
    config_dir: Path | None = None,
    local_files_only: bool = False,
    model: str | None = None,
) -> SummarizedMailEvent:
    """One-shot summarize using a fresh summarizer instance."""
    summarizer = EmailSummarizer(
        model=model,
        config_dir=config_dir,
        local_files_only=local_files_only,
    )
    return summarizer.summarize_event(event)
