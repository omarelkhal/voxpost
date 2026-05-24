# Model leaderboard (community)

Voxpost is **not limited to Qwen**. Any **local** Ollama tag or Hugging Face model that works with `[summarize] backend = "ollama"` or `transformers` can be tested. Maintainers mostly use **Qwen 3.5** today; **Phi**, **Gemma**, **Mistral**, **SmolLM**, and others are welcome.

This page tracks models ranked on the **24-case speech-check fixture suite** ([`speech_check/fixtures/`](../src/voxpost/speech_check/fixtures/)). Scores come from **human review** (your judgment + optional chat rubric), not from `--auto-grade` alone.

---

## Leaderboard

Sorted by **PASS count** (desc), then **WEAK**, then **FAIL**. Ties keep submission order.

| Rank | Model | Backend | Quant / notes | Hardware | PASS | WEAK | FAIL | Good for average PC? | Contributor | Date | Run log |
|------|-------|---------|---------------|----------|------|------|------|----------------------|-------------|------|---------|
| 1 | `qwen3.5:2b` | ollama | default pull | Linux x86_64, CPU (~20 cores) | 16 | 5 | 4 | Marginal | [omarelkhal](https://github.com/omarelkhal) | 2026-05-24 | [graded run](benchmarks/runs/qwen3.5-2b__ollama__24of24__complete__run-20260524-030239-ba3c98.md) (judge: Composer 2.5) |

**Average PC** = roughly **16 GB RAM**, **4–8 CPU cores**, optional **8 GB GPU** — say **Yes** / **Marginal** / **No** in your PR.

---

## How to contribute a new model

### 1. Pick a model **not already on the leaderboard**

Examples: `phi4-mini`, `gemma3:4b`, `mistral:7b`, `qwen3.5:4b-q4_K_M`, `smollm2:360m` — any local tag.  
**Do not** submit cloud-only tags (`*:cloud`, remote APIs).

### 2. Run the 24 fixtures

```bash
ollama pull YOUR_MODEL_TAG

# ~/.config/voxpost/voxpost.toml → backend = "ollama", model = YOUR_MODEL_TAG
voxpost summarize speech-check --model YOUR_MODEL_TAG
```

Runs **one fixture at a time** and **auto-creates** a markdown report. After each case:

- Terminal prints `[N/24] case_id — speakable line`
- The report file under `docs/benchmarks/runs/` is updated in place (safe to commit partial runs; **Ctrl+C** keeps what finished)

Use `--no-report` only if you want terminal output without a log file.

#### Required run log filename

Each run gets a unique **run id** (timestamp + random suffix) so the same model can be benchmarked many times without clobbering older logs:

```text
{model}__{backend}__{completed}of{total}__{status}__run-{YYYYMMDD-HHMMSS}-{hex}.md
```

Example (complete 24/24 Ollama run):

```text
qwen3.5-2b__ollama__24of24__complete__run-20260524-143052-a1b2c3.md
```

Partial / stopped early:

```text
qwen3.5-2b__ollama__12of24__stopped-early__run-20260524-143052-a1b2c3.md
```

Override path only if needed: `--report-file path/to/custom.md` (leaderboard PRs should use the auto name).

Use **default mode** (no `--auto-grade`). The markdown report includes metadata, progress table, and per-case speakable lines.

### 3. Score with the chat review prompt

Open **[contributing/MODEL_REVIEW_PROMPT.md](contributing/MODEL_REVIEW_PROMPT.md)** — copy the whole prompt into your judge chat (Claude, ChatGPT, **Composer 2.5**, etc.), then paste the **full markdown report file** underneath.

Record the **judge model name** in the report metadata and PR (e.g. *Judge model: Composer 2.5*).

The chat returns a **PASS / WEAK / FAIL** table and a short verdict. You remain responsible for sanity-checking it before opening a PR.

### 4. Open a PR

Include:

- [ ] New row in the **Leaderboard** table above (sorted correctly)
- [ ] Run log: auto-named `docs/benchmarks/runs/{model}__{backend}__{n}of{N}__….md` (with judge grades filled in)
- [ ] **Judge model** named in PR description and report metadata
- [ ] Hardware note (RAM, CPU, GPU, OS) in the PR description
- [ ] Confirm model is **fully local** (Ollama or HF cache on your machine)

Maintainers may re-run a subset before merging.

---

## Add new email fixtures

The suite is **24 cases** today (forwards, invoices, OTP, newsletters, multilingual mail, etc.). If your model fails on a **real production pattern** not covered:

1. Add a JSON fixture in [`src/voxpost/speech_check/fixtures/`](../src/voxpost/speech_check/fixtures/) with:
   - unique `case_id` (filename stem)
   - realistic `event` body (`from_address`, `subject`, `body`)
   - `intent` — what a good speakable line must convey
   - optional `must_mention_any` / `must_not_mention` for `--auto-grade` smoke tests
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
| **Auto markdown report** | Unique filename per run; model, backend, progress, status, run id |
| **Grade the markdown file** | Paste report into MODEL_REVIEW_PROMPT; not raw terminal output |
| **Name the judge model** | e.g. Composer 2.5 — in metadata and PR |
| **Small models welcome** | We **want** objective evidence when sub-4B models fail — that helps users pick wisely |

---

## Related

- [MODEL_REVIEW_PROMPT.md](contributing/MODEL_REVIEW_PROMPT.md) — paste into judge chat with the markdown report
- [BLOCK_3_SUMMARIZE.md](BLOCK_3_SUMMARIZE.md) — summarizer pipeline
- [README.md](../README.md) — configuration reference
