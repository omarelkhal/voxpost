# Model leaderboard (community)

Voxpost is **not limited to Qwen**. Any **local** Ollama tag or Hugging Face model that works with `[summarize] backend = "ollama"` or `transformers` can be tested. Maintainers mostly use **Qwen 3.5** today; **Phi**, **Gemma**, **Mistral**, **SmolLM**, and others are welcome.

This page tracks models ranked on the **24-case speech-check fixture suite** ([`speech_check_cases.py`](../src/voxpost/speech_check_cases.py)). Scores come from **human review** (your judgment + optional chat rubric), not from `--auto-grade` alone.

---

## Leaderboard

Sorted by **PASS count** (desc), then **WEAK**, then **FAIL**. Ties keep submission order.

| Rank | Model | Backend | Quant / notes | Hardware | PASS | WEAK | FAIL | Good for average PC? | Contributor | Date | Run log |
|------|-------|---------|---------------|----------|------|------|------|----------------------|-------------|------|---------|
| — | *No submissions yet* | | | | | | | | | | |

**Average PC** = roughly **16 GB RAM**, **4–8 CPU cores**, optional **8 GB GPU** — say **Yes** / **Marginal** / **No** in your PR.

---

## How to contribute a new model

### 1. Pick a model **not already on the leaderboard**

Examples: `phi4-mini`, `gemma3:4b`, `mistral:7b`, `qwen3.5:4b-q4_K_M`, `smollm2:360m` — any local tag.  
**Do not** submit cloud-only tags (`*:cloud`, remote APIs).

### 2. Run the 24 fixtures (manual output)

```bash
# Ollama (recommended path)
ollama pull YOUR_MODEL_TAG

# ~/.config/voxpost/voxpost.toml → backend = "ollama", model = YOUR_MODEL_TAG
voxpost summarize speech-check --model YOUR_MODEL_TAG --workers 1 \
  | tee docs/benchmarks/runs/YOUR_MODEL_TAG.txt
```

Use **default mode** (no `--auto-grade`). You get, for each case: **Intent**, **Body preview**, **Model summary**, and a line for your judgment.

Optional reference only (not official scoring):

```bash
voxpost summarize speech-check --model YOUR_MODEL_TAG --auto-grade --workers 1
```

### 3. Score with the chat review prompt

Open **[contributing/MODEL_REVIEW_PROMPT.md](contributing/MODEL_REVIEW_PROMPT.md)** — copy the whole prompt into Claude, ChatGPT, or similar, then paste your `speech-check` output underneath.

The chat returns a **PASS / WEAK / FAIL** table and a short verdict. You remain responsible for sanity-checking it before opening a PR.

### 4. Open a PR

Include:

- [ ] New row in the **Leaderboard** table above (sorted correctly)
- [ ] Run log: `docs/benchmarks/runs/YOUR_MODEL_TAG.txt`
- [ ] Hardware note (RAM, CPU, GPU, OS) in the PR description
- [ ] Confirm model is **fully local** (Ollama or HF cache on your machine)

Maintainers may re-run a subset before merging.

---

## Add new email fixtures

The suite is **24 cases** today (forwards, invoices, OTP, newsletters, multilingual mail, etc.). If your model fails on a **real production pattern** not covered:

1. Add a `SpeechCheckCase` in [`src/voxpost/speech_check_cases.py`](../src/voxpost/speech_check_cases.py) with:
   - unique `case_id`
   - realistic `NewMailEvent` body
   - `intent` — what a good speakable line must convey
2. Open a **separate PR** (or combine with a model run if the fixture motivated the test)
3. Re-run affected models after merge (leaderboard may shift)

Do not tune prompts or gates to pass only your new fixture — add scenarios that reflect real mail.

---

## Rules

| Rule | Why |
|------|-----|
| **Local inference only** | Matches Voxpost privacy model |
| **No `--auto-grade` as the official score** | Heuristics are for CI smoke tests; leaderboard is human + rubric |
| **One row per exact Ollama tag / HF id** | `qwen3.5:4b` and `qwen3.5:4b-q4_K_M` are separate entries |
| **Attach the run log** | Others can spot-check speakable lines |
| **Small models welcome** | We **want** objective evidence when sub-4B models fail — that helps users pick wisely |

---

## Related

- [MODEL_REVIEW_PROMPT.md](contributing/MODEL_REVIEW_PROMPT.md) — paste into chat with your run output
- [BLOCK_3_SUMMARIZE.md](BLOCK_3_SUMMARIZE.md) — summarizer pipeline
- [README.md](../README.md) — configuration reference
