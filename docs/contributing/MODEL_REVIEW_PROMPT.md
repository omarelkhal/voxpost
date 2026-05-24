# Chat prompt — review a Voxpost speech-check run

Use this when you tested a **new model** that is **not on the [leaderboard](../MODEL_LEADERBOARD.md)** yet.

## Steps

1. Run locally (default = manual review output):

   ```bash
   voxpost summarize speech-check --model YOUR_MODEL_TAG --workers 1 \
     | tee docs/benchmarks/runs/YOUR_MODEL_TAG.txt
   ```

2. Copy **everything below the line** into a chat (Claude, ChatGPT, etc.).

3. Paste the **full terminal output** from step 1 at the end where indicated.

4. Use the chat’s **PASS / WEAK / FAIL table** and **verdict** for your GitHub PR.

---

## Prompt (copy from here)

You are reviewing speakable lines for **Voxpost**, a local Gmail TTS companion. Each case is a fake email. The model must produce **one short line** a user hears aloud — not a summary paragraph.

### What “good” sounds like

- **Accurate** — correct sender name or org, real subject/intent; no invented dates, amounts, or actions
- **Speakable** — one or two sentences max; no bullet lists, markdown, `@` symbols, or “the sender”
- **Useful** — answers “who + what matters” (OTP, meeting moved, invoice due, rejection, forward from real sender)
- **Language** — matches configured speech language (usually English), **not** the email language unless that is intentional
- **No hallucination** — if the mail is vague, a brief honest line beats invented detail

### Grades

- **PASS** — would trust this spoken aloud daily
- **WEAK** — understandable but vague, wrong tone, minor entity slip, or too long for TTS
- **FAIL** — wrong sender/intent, hallucination, fallback-quality generic line, unreadable, or spam template on important mail

### Your tasks

1. For **each case** in the pasted run, assign PASS / WEAK / FAIL and one short reason.
2. Count totals (out of 24, or however many cases appear).
3. Say if this model is **recommended for an average desktop** (≈16 GB RAM, no huge GPU).
4. Compare briefly to what you’d expect from **small (<2B)** vs **mid (4B–9B)** models.
5. Output a **leaderboard row** in this exact markdown table format (fill in):

```markdown
| Rank | Model | Backend | Quant / notes | Hardware | PASS | WEAK | FAIL | Good for average PC? | Contributor | Date | Run log |
|------|-------|---------|---------------|----------|------|------|------|----------------------|-------------|------|---------|
| ? | YOUR_MODEL_TAG | ollama | | YOUR_RAM/CPU/GPU/OS | N | N | N | Yes/Marginal/No | YOUR_GH_HANDLE | YYYY-MM-DD | docs/benchmarks/runs/YOUR_MODEL_TAG.txt |
```

6. List the **3 worst cases** (case_id + why) — these help maintainers and future contributors.

### Input — Voxpost speech-check output

Paste the full `voxpost summarize speech-check` log below this line:

```
(paste here)
```

---

## After the chat

- If you disagree with the chat on any case, **your judgment wins** — adjust counts before the PR.
- Do not use cloud models or APIs to **generate** the speakable lines under test; only use chat to **grade** local output you already produced.
