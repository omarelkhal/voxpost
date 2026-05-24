# Chat prompt — review a Voxpost speech-check run

Use this when you tested a **new model** that is **not on the [leaderboard](../MODEL_LEADERBOARD.md)** yet.

## Steps

1. Run locally (markdown report is **automatic**):

   ```bash
   voxpost summarize speech-check --model YOUR_MODEL_TAG
   ```

   This runs **one fixture at a time** and writes a unique markdown file under `docs/benchmarks/runs/`, for example:

   ```text
   qwen3.5-2b__ollama__24of24__complete__run-20260524-143052-a1b2c3.md
   ```

   Filename encodes: **model**, **backend**, **cases completed / total**, **status**, **unique run id** (repeated runs never overwrite prior logs).

   Watch stderr for `[N/24]` after each case. **Ctrl+C** keeps a partial file (`12of24__stopped-early__…`).

2. Copy **everything below the line** into your **judge chat** (Claude, ChatGPT, Composer, etc.).

3. Paste the **full contents of the markdown report file** (not terminal output) where indicated.

4. Tell the judge which **model graded the run** (e.g. *Composer 2.5*, *Claude Sonnet*, *GPT-4o*) — add it to the report metadata and PR.

5. Use the chat’s **PASS / WEAK / FAIL table** and **verdict** for your GitHub PR.

---

## Prompt (copy from here)

You are reviewing speakable lines for **Voxpost**, a local Gmail TTS companion. Each case is a fake email. The model must produce **one short line** a user hears aloud — not a summary paragraph.

**You are the judge model.** The submitter will name you (e.g. Composer 2.5). Include that name in your verdict and in the suggested leaderboard row.

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

1. For **each case** in the pasted markdown report, assign PASS / WEAK / FAIL and one short reason.
2. Count totals (out of 24, or however many cases completed in the report).
3. Say if this model is **recommended for an average desktop** (≈16 GB RAM, no huge GPU).
4. Compare briefly to what you’d expect from **small (<2B)** vs **mid (4B–9B)** models.
5. Output a **leaderboard row** in this exact markdown table format (fill in):

```markdown
| Rank | Model | Backend | Quant / notes | Hardware | PASS | WEAK | FAIL | Good for average PC? | Contributor | Date | Run log |
|------|-------|---------|---------------|----------|------|------|------|----------------------|-------------|------|---------|
| ? | YOUR_MODEL_TAG | ollama | | YOUR_RAM/CPU/GPU/OS | N | N | N | Yes/Marginal/No | YOUR_GH_HANDLE | YYYY-MM-DD | docs/benchmarks/runs/MODEL__backend__24of24__complete__DATE.md |
```

6. List the **3 worst cases** (case_id + why) — these help maintainers and future contributors.
7. State **Judge model:** YOUR_NAME (the chat model doing this review).

### Input — Voxpost speech-check markdown report

Paste the **full markdown file** from `docs/benchmarks/runs/` below this line:

```markdown
(paste entire .md report here)
```

---

## After the chat

- If you disagree with the chat on any case, **your judgment wins** — adjust counts before the PR.
- Do not use cloud models or APIs to **generate** the speakable lines under test; only use chat to **grade** local output you already produced.
- Commit the graded report (with judge grades filled in) or attach it to the PR alongside the leaderboard row.
