# Prompt engineering brief: Voxpost email → spoken assistant line

Brief for a prompt engineer (human or LLM) refining Voxpost Block 3 summarization prompts.

## Your role

You are an expert prompt engineer for **small instruction-tuned chat models** (0.8B–2B parameters, running on CPU in a desktop app). Your job is to design and refine the **system + user prompt contract** so the model outputs a single **spoken assistant briefing** per incoming email — not a neutral summary.

**Success criterion:** A human would happily hear the line aloud when new mail arrives, without reading the email. Manual review on **24 diverse fixture emails** is the bar; automated keyword grading is a weak sanity check only.

## Product context

**Voxpost** is a local Gmail companion: new mail → summarize in memory → speak via on-device TTS → discard. No mail storage. Summarization must run **100% on-device** after model download (privacy). Cloud LLM APIs are **dev-only oracles** for prompt validation, not production.

The user configures **spoken output language** in `voxpost.toml` (e.g. `target_lang = en`). The briefing must **always** be in that language, **even when the email is French, Spanish, German, etc.**

Output goes to **Supertonic TTS**. Numbers, times, and OTP codes must be TTS-friendly (e.g. “three p.m.” not “3:00 PM”, “four four two one” for invoice numbers when needed).

## What the model must produce

**One block of natural spoken prose** — no JSON, no labels, no “Here is a summary”, no thinking blocks, no markdown.

**Intent-first assistant voice:** decide what the listener most needs to hear.

| Situation | Good pattern |
|-----------|----------------|
| Spam / marketing newsletter | Brief: “This looks like spam about …” |
| Important / actionable mail | Who, what, deadline, required action |
| Forwarded mail | Name the **original sender**, never the Gmail forwarder |
| Security alert | Treat as urgent; say what happened and what to do |
| Booking / invoice / tax / interview | Concrete doc, amount, date/time, place, deadline |
| Short ping (“Did you get the doc?”) | One tight sentence |
| Long official letter | Multiple short sentences OK; don’t drop dates or limits |

**Length adapts to email size:**

- ≤50 words body → one brief sentence
- 51–120 words → one or two sentences
- \>120 words → as many short sentences as needed; don’t omit deadlines, venues, or actions

**Hard bans:**

- Vague phrasing: “the sender”, “sent a message saying”, “about booking”
- Email addresses or `@` symbols
- Invented urgency or details not in the email
- Promotional CTAs like “you should buy…”
- Output in the email’s language when config says English (or other configured lang)
- Reasoning / thinking traces (Qwen3.5 models leak these if not constrained)

## Current prompt architecture (what you are improving)

**Chat format:** system message + user message.

**System prompt** is assembled from four blocks (in order). Source: `src/voxpost/summarize.py` (`_chat_system_prompt`).

### 1. Language lock

```text
Output language: {lang} only. Never reply in the email's language — always use {lang} from the user config.
```

### 2. Core contract (`_SPEAKABLE_CONTRACT_CORE`)

```text
You are a voice assistant for incoming email. Your output is one spoken assistant briefing for someone who cannot see the email. Decide what they most need to hear — not a neutral summary. Use only facts from the email. If it is obvious spam or noise, say so plainly (for example: this looks like spam about …). If it is important or needs action, say what matters and why. Match the situation with natural phrasing: a booking confirmation arrived; you got a job offer; don't forget a reminder; someone is asking whether …; an official document is ready with a deadline. Name the true author when useful: original sender, signatory, company, or official service — never the Gmail forwarder on forwarded mail. For official, legal, security, invoice, application, booking, or event mail, include the concrete document or topic, any deadline or date and time, place if relevant, and the required action or limit when present (for example download window or retry count). Do not use vague wording like 'sent a message saying', 'about booking', 'the sender', or email addresses. Do not invent urgency, details, or promotional calls to action like 'you should'. Write natural spoken prose — not JSON, not labels, not meta narration.
```

### 3. Length guidance (by body word count)

- ≤50 words: one brief sentence — spam, request, confirmation, reminder, or alert; true author if useful
- 51–120 words: one or two sentences — what happened, why it matters, author, date/time/deadline/action
- \>120 words: as many short sentences as needed; do not omit dates, venues, limits, or artificially shorten

### 4. TTS number rules (English example)

```text
Always reply in en only — the configured output language from voxpost.toml, never the email language. Write every number as spoken words for text-to-speech, never digits: verification and OTP codes digit by digit; money in full words with currency; other counts as whole numbers unless digit-by-digit is clearer.
```

### Plain user message template

```text
Write the spoken assistant briefing for this email:

From: {from_address}
Subject: {subject}
Body: {cleaned_body}
```

### Structured variant (optional)

JSON input with `original_sender`, `is_forward`, `signatory_name`, `company`, `application_role`, attachment metadata — same output contract. Built in `summarizer_context.py`; toggled via `[summarize] chat_input_format = plain | structured`.

### Inference settings (small models)

- `temperature=0`
- `max_new_tokens`: 96 / 128 / 160 by body length (see `hf_inference_prompt.py` and local chat-LM path)

## Evaluation set (24 fixtures)

Fixtures live in `src/voxpost/speech_check_cases.py`.

| Case ID | Scenario |
|---------|----------|
| `fr_forward_phone` | French forward — client asks for phone number |
| `en_deploy_alert` | English — staging deploy failed |
| `en_short_ack` | English — short acknowledgment |
| `fr_meeting_move` | French — meeting moved to Thursday |
| `en_invoice_due` | English — invoice payment due |
| `en_forward_partner` | English forward — account manager intro |
| `es_delivery` | Spanish — package delivery window |
| `en_security_alert` | English — sign-in from new device |
| `fr_complaint` | French — product complaint |
| `en_minimal_ping` | English — one-line ping |
| `en_newsletter_noise` | English — newsletter marketing (noise) |
| `de_tax_notice` | German — tax assessment notice |
| `pt_hotel_confirm` | Portuguese — hotel booking confirmation |
| `en_ooo_autoreply` | English — out-of-office auto-reply |
| `en_github_pr` | English — GitHub pull request review |
| `en_rent_increase` | English — landlord rent increase letter |
| `it_dinner_invite` | Italian — informal dinner invitation |
| `en_api_bullet_list` | English — three numbered API questions |
| `en_subject_only_flight` | English — subject-only flight cancellation |
| `en_angry_order` | English — angry ALL CAPS order complaint |
| `nl_interview_invite` | Dutch — job interview invitation |
| `en_school_snow_day` | English — school closure alert |
| `en_dentist_reminder` | English — dental appointment reminder |
| `ja_en_mixed_vendor` | Mixed JP/EN — vendor shipment delay |

Each fixture has: **intent description**, **must_mention_any** keywords, **must_not_mention** forbidden hallucinations, **max_words** (40 default for auto-grade).

## Known results (do not overfit auto-grade)

| Model | Role | Result |
|-------|------|--------|
| **Qwen3-235B** (HF oracle) | Same prompts | **~21/24 manual quality** — contract is basically sound |
| **Qwen3.5-2B** (HF Featherless) | Same prompts | **24/24 auto PASS but ~9 false “spam” labels** on important mail |
| **Qwen3.5-0.8B** (local) | Same prompts | Thinking leaks, wrong output language, vague fallbacks |

### 235B good vs 2B bad (same email, same prompt)

| Case | 235B (good) | 2B (bad) |
|------|-------------|----------|
| French forward asking for phone | “personal message from a client asking for your phone number” | “This looks like spam about a phone number” |
| Security sign-in from Berlin | “Security alert… reset password if not you” | “This looks like spam about a sign-in from Berlin” |
| School snow day closure | “Lincoln Elementary closed Thursday… remote on Teams” | “This looks like spam about school closures” |
| Angry customer order #99281 | Describes complaint + callback demand | “This looks like spam about an unpaid order” |

**Root issue to fix in prompts:** Small models **over-trigger the spam template** whenever the line “If it is obvious spam…” appears. They need clearer **decision rules**: spam = marketing/newsletters/automated promos; **not** forwards, security alerts, complaints, school alerts, interviews, invoices, etc.

Secondary issues: **language lock** on multilingual bodies; **Qwen3.5 thinking blocks** in output; **time errors** (4 PM → 4 AM).

## Target deployment models (optimize for these)

Primary candidates: **Qwen/Qwen3.5-0.8B**, **Qwen/Qwen3.5-2B** (~2–4.5 GB, CPU, mass-market RAM).

Prompt must work on **small models**, not only 235B. Shorter, clearer rules beat long prose. Few-shot examples in-system may help if token budget allows.

Oracle for prompt iteration: `Qwen/Qwen3-235B-A22B-Instruct-2507` via HF Inference (dev only).

## What we need from you

Deliver **all** of the following:

1. **Revised system prompt** (plain + structured variants if they differ), ready to drop into Python string constants in `summarize.py`.
2. **Revised user message template** (if needed), in `hf_inference_prompt.py` / local chat path.
3. **Explicit spam vs important decision rubric** — bullet rules or a tiny decision tree small models can follow.
4. **3–5 few-shot examples** (input snippet → ideal spoken line) covering: newsletter spam, security alert, forward, interview invite, angry customer.
5. **Anti-patterns list** — phrases to never output.
6. **Notes for Qwen3.5** — how to suppress thinking/reasoning in output (no ``, no “Thinking Process”).
7. **Regression table**: for each of the 24 fixture **intents**, one example ideal line (English output, `target_lang=en`).

**Constraints:**

- Do not require cloud APIs or tools in production.
- Do not add attachment body content (metadata only in structured JSON).
- Prefer rules small models obey over nuanced prose only big models understand.
- Keep total system prompt under ~800–1200 tokens if possible.

## How we will validate your prompt

```bash
# Dev oracle (cloud, same prompts)
uv run voxpost summarize prompt-check --model Qwen/Qwen3-235B-A22B-Instruct-2507

# Small model on HF (Featherless — auto-routing does not support Qwen3.5-2B on all accounts)
uv run voxpost summarize prompt-check --model Qwen/Qwen3.5-2B --provider featherless-ai

# Local (production path)
uv run voxpost summarize speech-check --model Qwen/Qwen3.5-0.8B --workers 1
```

**Manual review** is authoritative. Auto-grade PASS with “spam” on important mail = **failure**.

## Example ideal outputs (reference tone)

**Email:** Staging deploy failed, migration timed out, check pipeline logs.

**Ideal line:** “The staging deploy failed around nine forty-five a.m. due to a migration timeout — Alex Chen asked you to check the pipeline logs when you can.”

**Email:** Marketing newsletter 50% off sale.

**Ideal line:** “This looks like spam about a fifty percent off sale.”

**Email:** Sign-in from Berlin at 02:14 UTC, reset password if not you.

**Ideal line:** “Security alert: someone signed in to your account from Berlin at two fourteen a.m. UTC — reset your password if that wasn’t you.”

## One-line ask

Design the best system + user prompt for a **local 0.8B–2B chat model** that turns any incoming email into **one TTS-ready assistant briefing in a fixed config language**, with **strict spam-vs-important classification** (newsletters only), **forward-aware sender naming**, **length-adaptive detail**, and **no thinking leaks** — validated against **24 diverse email fixtures** where a **235B oracle already proves the intent contract works** but **2B mislabels important mail as spam**.
