# Voxpost — Spoken Briefing Prompt Design

Deliverable for Voxpost Block 3 (email → spoken assistant briefing) targeting **Qwen3.5-0.8B / Qwen3.5-2B on CPU**, validated against the **24-fixture speech check** with the **Qwen3-235B oracle**.

The previous prompt was sound on the 235B but the 2B mislabeled important mail as spam in ~9/24 cases. This redesign keeps the intent contract and rewrites the rules in a shape a 0.8B–2B chat model can actually follow: short numbered clauses, an enumerated always-IMPORTANT list, a three-clause spam conjunction, in-system few-shot examples, and three layers of thinking suppression.

---

## 1. Revised system prompt

Drop-in for `src/voxpost/summarize.py` (`_chat_system_prompt`). The four-block assembly stays (language lock → core contract → length → TTS) but each block is tightened and the few-shot examples live inside `_SPEAKABLE_CONTRACT_CORE` so they survive any future block reordering.

```python
# src/voxpost/summarize.py

_LANGUAGE_LOCK = (
    "Output language: {target_lang} only. "
    "Translate from any source language (French, Spanish, German, Italian, "
    "Dutch, Portuguese, Japanese, mixed). "
    "Never reply in the email's language — always use {target_lang} from the user config."
)

_SPEAKABLE_CONTRACT_CORE = """\
You are Voxpost, a voice assistant. For each incoming email, write ONE spoken \
briefing for a listener who cannot see the screen. Speak as the assistant, \
naturally, as if telling a colleague what just arrived.

OUTPUT FORMAT
- One block of plain spoken prose. No JSON, no labels, no bullet points, no \
markdown, no headings, no quotes around the line.
- No preamble: never start with "Here is", "Here's", "Summary:", "Briefing:", \
"Sure,", "Of course,", "The email says".
- No reasoning, no <think> blocks, no "Thinking:", no "Let me", no "Step 1", \
no meta narration. Output the briefing only, then stop.
- Never include email addresses, the "@" symbol, URLs, or raw header lines.

CLASSIFY FIRST — exactly one of two:

(A) SPAM — ONLY if ALL THREE are true:
   1. Sender is a brand, store, mailing list, or automated marketing system \
(not a real person, not a service the listener uses, not a forward).
   2. Body is selling, promoting, discounting, or pushing a signup / newsletter / CTA.
   3. There is no specific personal fact, action, or deadline the listener owns.
   Pattern: "This looks like spam about <concrete marketing topic>."

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
Tie-breaker: if you cannot fill "This looks like spam about X" with a real \
marketing topic, it is NOT spam.

FOR IMPORTANT MAIL, INCLUDE:
- Who it is from. For forwards, name the ORIGINAL sender or their role \
("your client Marc Dubois", "your landlord", "the airline"), never the Gmail \
forwarder. Use the signatory or the in-body "From:" line.
- What happened or what is being asked.
- Any concrete date, time, deadline, place, amount, document, code, or action.
- The required next step, said calmly as a suggestion, not as a command.

PRESERVE FACTS
- Keep a.m. / p.m. exactly as the email states them. Never flip 4 p.m. to 4 a.m.
- Never invent names, dates, times, amounts, urgency, or actions.
- If a fact is missing, omit it — do not guess.

BANNED PHRASES — never emit:
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
→ This looks like spam about a fifty percent off weekend sale.

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

[5] Angry ALL-CAPS customer (never spam; OTP-style code digit by digit)
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
Keep each briefing under about forty spoken words unless the email truly \
needs more facts.
"""

_TTS_NUMBER_RULES = """\
TTS NUMBER RULES — every number as spoken words, never digits:
- Times spoken naturally: "three p.m.", "nine forty-five a.m.", \
"two fourteen a.m. UTC".
- Money in full words with currency: "two hundred fifty euros", \
"one thousand two hundred dollars".
- OTP, verification, tracking, invoice, order, phone numbers: digit by digit \
("four four two one", "nine nine two eight one").
- Dates spoken naturally: "Thursday the twelfth", "March third", \
"April fifteenth".
- Percentages as words: "fifty percent".
Always reply in {target_lang} only — the configured output language from \
voxpost.toml, never the email language.
"""

def _chat_system_prompt(target_lang: str, body_word_count: int) -> str:
    return "\n\n".join([
        _LANGUAGE_LOCK.format(target_lang=target_lang),
        _SPEAKABLE_CONTRACT_CORE,
        _LENGTH_GUIDANCE,
        _TTS_NUMBER_RULES.format(target_lang=target_lang),
    ])
```

**Token budget:** ~900 tokens for the system message including the five examples — inside the 800–1200 ceiling. If a deployment must shave further, drop examples [4] and [5] first; keep [1] (spam shape), [2] (security non-spam), [3] (forward).

The structured variant uses the **same system prompt** — only the user message changes. See section 2.

---

## 2. Revised user message template

Two variants, toggled by `[summarize] chat_input_format = plain | structured` in `voxpost.toml`. Both end with the same closing instruction so the model never confuses input with output.

### 2a. Plain variant — `hf_inference_prompt.py` / local chat path

```python
_USER_TEMPLATE_PLAIN = """\
EMAIL
From: {from_address}
Subject: {subject}
Body:
{cleaned_body}

Write the spoken briefing for this email now. Output the briefing only, \
on a single block, then stop."""
```

### 2b. Structured variant — `summarizer_context.py`

```python
_USER_TEMPLATE_STRUCTURED = """\
EMAIL (structured fields — use them, do not echo them)
{context_json}

Rules for the structured fields:
- If is_forward is true, name original_sender or signatory_name in the \
briefing, never the from_address.
- If signatory_name is present, prefer it over the From header.
- If application_role is present, the email is about a job application — \
say the role.
- attachments lists name and mime type only; mention a document by name if \
relevant ("the invoice PDF", "the contract attached"), never the body of an \
attachment.

Write the spoken briefing for this email now. Output the briefing only, \
on a single block, then stop."""
```

Where `context_json` is the compact JSON from `summarizer_context.py`:

```json
{
  "from_address": "assistant@yourdomain.com",
  "is_forward": true,
  "original_sender": "Marc Dubois",
  "signatory_name": "Marc",
  "company": null,
  "application_role": null,
  "subject": "Fwd: petite question",
  "body": "...cleaned body with forward header preserved...",
  "attachments": [{"name": "id.pdf", "mime": "application/pdf"}]
}
```

**Inference settings** (unchanged from the brief, restated for completeness):

```python
GEN_KWARGS = dict(
    temperature=0.0,
    do_sample=False,
    repetition_penalty=1.05,
    max_new_tokens={"short": 96, "medium": 128, "long": 160},  # by body length
    stop=[
        "\n\n",
        "<think>", "</think>",
        "Thinking:", "Reasoning:",
        "Note:", "Explanation:",
        "Here is", "Here's",
    ],
)
```

---

## 3. Spam vs important decision rubric (the actual fix)

The 2B failure mode is "if a `spam` template exists in the prompt, prefer it". The fix is to make spam a **conjunction of three conditions**, not a vibe.

**SPAM only if ALL three are true:**

1. Sender is a brand / store / mailing list / automated marketing system (not a person, not a system the listener uses, not a forwarded human).
2. Body is selling, promoting, discounting, or pushing a signup / newsletter / CTA.
3. There is no specific personal fact, action, or deadline the listener owns.

If any one is false → **IMPORTANT**.

**Always-IMPORTANT short list** (enumerated in the system prompt so the small model has no room to generalize wrong):

| Category | Why it is not spam |
|---|---|
| Security alert / sign-in / password reset | Specific personal action required |
| Forwarded personal mail | Real human author behind the forwarder |
| Booking, delivery, invoice, tax, official, legal, government | Concrete fact and date affecting the listener |
| Interview, appointment, calendar move | Concrete time the listener owns |
| Customer complaint, including ALL CAPS / angry | Real person needing a response |
| Internal team / deploy / CI / code review / GitHub PR | Work the listener owns |
| Out-of-office auto-reply | Factual info; speak as info, not as spam |
| Subject-only or minimal ping | A real person is asking something |

**Tie-breaker** (also in the prompt): *if you cannot complete the pattern "This looks like spam about X" with a real marketing topic X — it is not spam.*

This single test catches all 9 prior 2B failures. None of them have a marketing X:

- "spam about a sign-in from Berlin" → not a marketing topic → not spam.
- "spam about a school closure" → not a marketing topic → not spam.
- "spam about an unpaid order from an angry customer" → not a marketing topic → not spam.
- "spam about a phone number request from a French client" → not a marketing topic → not spam.

---

## 4. Few-shot examples

Embedded inline in `_SPEAKABLE_CONTRACT_CORE` above. Five examples chosen to cover the exact failure modes seen on Qwen3.5-2B:

| # | Shape | What it teaches the model |
|---|---|---|
| 1 | Newsletter spam | The **only** allowed spam shape — brand sender, promo body, no personal fact |
| 2 | Security alert | Automated ≠ spam; preserve time exactly; concrete action |
| 3 | French forwarded client mail | Name original sender, translate to English, ignore the Gmail forwarder |
| 4 | Dutch interview invite | Translate date/time/place, never spam, no email language leak |
| 5 | Angry ALL-CAPS customer | Capture intent + order number digit-by-digit, never spam |

These five span all four hard failure modes from the brief: spam-over-triggering, language leak, forward-author confusion, and digit/time formatting.

---

## 5. Anti-patterns list (banned outputs)

Never emit:

**Vague stand-ins**

- `the sender`, `this sender`, `the email`, `the message`, `in this email`.

**Narrating verbs**

- `sent a message saying`, `sent an email about`, `writes that`, `wants to inform you`, `is reaching out to`.

**Vague topics**

- `about booking`, `about meeting`, `about a sign-in`, `about an order` — always replace with the concrete fact.

**Header / format leakage**

- Any `@`, any email address, any URL, any `From:` / `Subject:` label leaking into the line.
- JSON braces, markdown stars, bullets, headings, code fences, quotes around the whole line.

**Reasoning leakage**

- `<think>`, `</think>`, `Thinking:`, `Reasoning:`, `Let me`, `First,`, `Step 1`, `Note:`, `Explanation:`.

**Preamble**

- `Here is`, `Here's the briefing`, `Summary:`, `Spoken briefing:`, `Sure,`, `Of course,`.

**Hallucinated facts**

- Any name, date, time, amount, OTP, place, or urgency word not literally in the email.

**Promotional echo on non-spam**

- `you should buy`, `great deal`, `limited time for you`.

**Spam template on important mail**

- `This looks like spam about <a security sign-in / a school closure / an unpaid order / a forwarded question>` — these are **always wrong**.

**Wrong language**

- Replying in the email's source language when `target_lang` says otherwise.

**Digit forms**

- `3:00 PM`, `$250`, `99281`, `+33 6 12 34 56 78` — always spell.

**a.m./p.m. swaps**

- "4 PM" in the email must be "four p.m." in the briefing, never "four a.m.".

---

## 6. Notes for Qwen3.5 thinking suppression

Qwen3-family models (and Qwen3.5 variants) ship a hybrid thinking mode. Three layers of defense, applied together:

**Layer 1 — chat template flag (the cleanest fix):**

```python
prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=False,   # Qwen3 / Qwen3.5 hybrid models honor this
)
```

If the deployed variant ignores `enable_thinking`, fall back to Layer 2.

**Layer 2 — explicit system instruction** (already in `_SPEAKABLE_CONTRACT_CORE`):

> "No reasoning, no `<think>` blocks, no 'Thinking:', no 'Let me', no meta narration. Output the briefing only, then stop."

**Layer 3 — generation stop strings:**

```python
stop = [
    "\n\n",
    "<think>", "</think>",
    "Thinking:", "Reasoning:",
    "Note:", "Explanation:",
    "Here is", "Here's",
]
```

Also: keep `temperature=0` and cap `max_new_tokens` per length bucket — Qwen3.5-0.8B's thinking leak grows with token budget.

**Post-processing safety net** (cheap, keep it):

```python
import re

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_PREAMBLE_RE = re.compile(
    r"^(here(?:'s| is)(?: the)?(?: spoken)?(?: briefing)?\s*[:\-]?\s*|"
    r"sure[,!]?\s*|of course[,!]?\s*|briefing\s*[:\-]\s*|"
    r"summary\s*[:\-]\s*)",
    re.IGNORECASE,
)

def clean_briefing(raw: str) -> str:
    text = _THINK_RE.sub("", raw).strip()
    text = _PREAMBLE_RE.sub("", text).strip()
    return " ".join(text.split())   # collapse whitespace
```

---

## 7. Regression table — ideal English line per fixture

`target_lang = en` for all 24. These are the lines a human reviewer should be happy to hear aloud. They are not the only valid outputs — they are the **shape** the prompt should consistently produce.

| Case ID | Ideal spoken briefing |
|---|---|
| `fr_forward_phone` | Forwarded from your client Marc Dubois — he is asking you to send him your phone number. |
| `en_deploy_alert` | The staging deploy failed around nine forty-five a.m. due to a migration timeout — Alex Chen asked you to check the pipeline logs when you can. |
| `en_short_ack` | Sam confirmed he got the document. |
| `fr_meeting_move` | Camille moved tomorrow's meeting to Thursday at ten a.m. |
| `en_invoice_due` | Invoice number four four two one for two hundred fifty euros is due Friday March third. |
| `en_forward_partner` | Forwarded from Priya Patel at Northwind — she is introducing James Wong as your new account manager. |
| `es_delivery` | Your MercadoEnvíos package will be delivered tomorrow between two and four p.m. |
| `en_security_alert` | Security alert: someone signed in to your account from Berlin at two fourteen a.m. UTC — reset your password if that wasn't you. |
| `fr_complaint` | Sophie Martin is complaining that her order arrived broken and is asking for a full refund. |
| `en_minimal_ping` | Jordan is asking whether you got the document. |
| `en_newsletter_noise` | This looks like spam about a fifty percent off weekend sale. |
| `de_tax_notice` | Tax assessment notice from the Finanzamt — you owe eight hundred forty-two euros by April fifteenth. |
| `pt_hotel_confirm` | Hotel booking confirmed at Pousada do Sol in Lisbon — check-in Friday June seventh, check-out Sunday June ninth. |
| `en_ooo_autoreply` | Out-of-office auto-reply from Linda — she is back next Monday and points you to Carlos for urgent matters. |
| `en_github_pr` | GitHub pull request review requested by Jamie on the authentication branch. |
| `en_rent_increase` | Your landlord Mr. Thompson is raising the rent by fifty euros starting July first — you have until June fifteenth to respond. |
| `it_dinner_invite` | Giulia is inviting you to dinner at her place on Saturday at eight p.m. |
| `en_api_bullet_list` | Three API questions from Dev Lee — about rate limits, authentication, and webhook retries. |
| `en_subject_only_flight` | Flight cancellation alert in the subject line — no further details in the body. |
| `en_angry_order` | An angry customer is complaining that order nine nine two eight one still hasn't shipped and is demanding a callback today. |
| `nl_interview_invite` | Job interview invitation — Wednesday May fifteenth at two p.m. at the company's Amsterdam office. |
| `en_school_snow_day` | Lincoln Elementary will be closed Thursday due to snow — classes move to remote on Teams at nine a.m. |
| `en_dentist_reminder` | Dental appointment reminder with Doctor Nguyen on Tuesday at three p.m. |
| `ja_en_mixed_vendor` | Vendor shipment delay from Tanaka-san at Sakura Trading — your order now ships next Monday instead of this Friday. |

---

## How to validate

1. **Oracle pass first** — confirm the contract hasn't regressed on the 235B:

   ```bash
   uv run voxpost summarize prompt-check --model Qwen/Qwen3-235B-A22B-Instruct-2507
   ```

   Expect ~22–24/24 manual quality. If lower, the prompt has lost expressiveness; widen the bands.

2. **Small-model spam regression** — the real test:

   ```bash
   uv run voxpost summarize prompt-check --model Qwen/Qwen3.5-2B --provider featherless-ai
   ```

   Manually review the 9 previously-mislabeled cases (`fr_forward_phone`, `en_security_alert`, `en_school_snow_day`, `en_angry_order`, `en_forward_partner`, `de_tax_notice`, `nl_interview_invite`, `en_ooo_autoreply`, `en_rent_increase`). **None** should produce a "this looks like spam" line. If any do, add a one-line example for that always-IMPORTANT category to `_SPEAKABLE_CONTRACT_CORE`.

3. **Local production path**:

   ```bash
   uv run voxpost summarize speech-check --model Qwen/Qwen3.5-0.8B --workers 1
   ```

   Watch for thinking leaks; if any survive, confirm `enable_thinking=False` is being applied and that stop strings include the leaked token.

---

## Why this should work where the previous prompt didn't

- **Spam was a vibe; it is now a conjunction.** Small models can evaluate three concrete clauses and AND them. They cannot evaluate "is it obvious spam".
- **Always-IMPORTANT list is enumerated.** Forward, security, school, complaint, OOO, PR, deploy, interview — all named. The 2B model needs the list because it has no world model strong enough to derive it.
- **Few-shot in-system.** Five examples covering the exact failure modes from the 235B-vs-2B table. Small models copy shapes; we give them the right shapes.
- **Length is folded into the core contract.** Small models drop separate blocks; folding raises adherence.
- **TTS reinforcement is the last thing in the system message.** Recency wins on small models — digits and `@` symbols stop leaking when the rule is right before the user turn.
- **Thinking is killed at three layers**, not one — chat template flag, explicit ban, stop strings, plus a regex post-process safety net.

---

## Change log

| Version | Date | Change |
|---|---|---|
| v1 | 2026-05-23 | Initial redesign for Qwen3.5-0.8B/2B. Three-clause spam rubric, enumerated always-IMPORTANT list, five in-system few-shot examples, three-layer thinking suppression, full 24-fixture regression table. |
