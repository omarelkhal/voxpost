# Model leaderboard (community)

Voxpost is **not limited to Qwen**. Any **local** Ollama tag or Hugging Face model that works with `[summarize] backend = "ollama"` or `transformers` can be tested. Maintainers mostly use **Qwen 3.5** today; **Phi**, **Gemma**, **Mistral**, **SmolLM**, and others are welcome.

This page tracks models ranked on the **24-case speech-check fixture suite** ([`speech_check/fixtures/`](../src/voxpost/speech_check/fixtures/)). Scores come from **human review** (your judgment + optional chat rubric), not from `--auto-grade` alone.

---

## Leaderboard

Sorted by **PASS count** (desc), then **WEAK**, then **FAIL**. Ties keep submission order.

| Rank | Model | Backend | Input lang | Output lang | Quant / notes | Hardware | PASS | WEAK | FAIL | Good for average PC? | Contributor | Date | Run log |
|------|-------|---------|------------|-------------|---------------|----------|------|------|------|----------------------|-------------|------|---------|
| 1 | `qwen3.5:2b` | ollama | multi | en | default pull | Linux x86_64, CPU (~20 cores) | 16 | 5 | 4 | Marginal | [omarelkhal](https://github.com/omarelkhal) | 2026-05-24 | [graded run](benchmarks/runs/qwen3.5-2b__ollama__24of24__complete__run-20260524-030239-ba3c98.md) (judge: Composer 2.5) |

**Input lang** = email/fixture filter (`multi` = full 24-case multilingual suite; `en` = English fixtures only, etc.). **Output lang** = speakable-line / TTS language (Supertonic code). Compare scores only when both match.

See [Speech-check language configuration](contributing/SPEECH_CHECK_CONFIG.md) for flags and allowed codes.

**Average PC** = roughly **16 GB RAM**, **4–8 CPU cores**, optional **8 GB GPU** — say **Yes** / **Marginal** / **No** in your PR.

---

## Suggested models to benchmark

Objective shortlist for contributors — **exact Ollama tags** verified on [ollama.com/library](https://ollama.com/library) (May 2026). Matching **Hugging Face ids** are for `[summarize] backend = "transformers"` only; leaderboard rows use the **Ollama tag** when you run via Ollama.

### Eligibility

| Allowed | Not allowed |
|---------|-------------|
| Local Ollama pull (`ollama pull …`) | Any `*:cloud` tag (e.g. `qwen3.5:cloud`, `gemma3:4b-cloud`, `gpt-oss:20b-cloud`, `ministral-3:8b-cloud`) |
| Local HF cache + `transformers` | ChatGPT, GPT-4, or any remote inference API |
| Open-weight **gpt-oss** via Ollama/HF | HF `prompt-check` / cloud oracle runs (dev-only; not leaderboard rows) |

**ChatGPT is not a benchmark target.** For OpenAI open weights locally, use **`gpt-oss:20b`** (Ollama) or **`openai/gpt-oss-20b`** (HF) — not the commercial API.

Gemma weights on HF are **gated** (accept Google’s license once per account before `transformers` download).

### Priority A — daily-driver band (≤ ~4B, average PC)

Best coverage per watt; matches Voxpost’s listen/summarize target hardware.

| Ollama tag | HF id (`transformers`) | ~Pull | Why test | Leaderboard |
|------------|------------------------|-------|----------|-------------|
| `qwen3.5:0.8b` | `Qwen/Qwen3.5-0.8B` | ~1.0 GB | Maintainer CPU listen default; smallest Qwen 3.5 | — |
| `qwen3.5:2b` | `Qwen/Qwen3.5-2B` | ~2.7 GB | Strong small chat-LM; reference run exists | **Done** (16/5/4) |
| `qwen3.5:4b` | `Qwen/Qwen3.5-4B` | ~3.4 GB | Likely best quality in sub-5B if CPU/RAM allows | — |
| `phi4-mini` | `microsoft/Phi-4-mini-instruct` | ~2.5 GB | Same as `phi4-mini:3.8b` on Ollama; multilingual instruct | — |
| `gemma3:1b` | `google/gemma-3-1b-it` | ~815 MB | Tiny Google instruct; gated on HF | — |
| `gemma3:4b` | `google/gemma-3-4b-it` | ~3.3 GB | Strong 4B instruct; gated on HF | — |
| `smollm2:1.7b` | `HuggingFaceTB/SmolLM2-1.7B-Instruct` | ~1.8 GB | HF tiny instruct baseline; 8K context on Ollama | — |
| `llama3.2:3b` | `meta-llama/Llama-3.2-3B-Instruct` | ~2.0 GB | Common Meta small instruct; gated on HF | — |

Quant variants (separate leaderboard rows): e.g. `qwen3.5:2b-q4_K_M`, `qwen3.5:4b-q4_K_M`, `gemma3:4b-it-q4_K_M`.

### Priority B — mid-size (8–12B, 16–32 GB RAM or GPU)

| Ollama tag | HF id (`transformers`) | ~Pull | Why test | Leaderboard |
|------------|------------------------|-------|----------|-------------|
| `qwen3.5:9b` | `Qwen/Qwen3.5-9B` | ~6.6 GB | Upper bound for “enthusiast” desktop | — |
| `mistral:7b` | `mistralai/Mistral-7B-Instruct-v0.3` | ~4.4 GB | Classic 7B instruct (`mistral:7b` = v0.3 q4_K_M on Ollama) | — |
| `ministral-3:8b` | `mistralai/Ministral-3-8B-Instruct-2512` | ~6.0 GB | Current Mistral edge line (Dec 2025) | — |
| `mistral-nemo:12b` | `mistralai/Mistral-Nemo-Instruct-2407` | ~7.1 GB | Same as `mistral-nemo:latest`; 12B Mistral×NVIDIA | — |

### Priority C — heavy local (workstation / 24 GB+ VRAM)

| Ollama tag | HF id (`transformers`) | ~Pull | Why test | Leaderboard |
|------------|------------------------|-------|----------|-------------|
| `gpt-oss:20b` | `openai/gpt-oss-20b` | ~14 GB | Open-weight MoE; local only — **not** ChatGPT API | — |
| `qwen3.5:27b` | `Qwen/Qwen3.5-27B` | ~17 GB | Quality ceiling for all-local Qwen 3.5 | — |
| `gemma3:12b` | `google/gemma-3-12b-it` | ~8.1 GB | Larger Gemma instruct; gated on HF | — |

### Priority D — intentional weak baselines

Useful floor scores; expect many FAILs — that data helps users avoid bad defaults.

| Ollama tag | HF id (`transformers`) | ~Pull | Why test | Leaderboard |
|------------|------------------------|-------|----------|-------------|
| `smollm2:360m` | `HuggingFaceTB/SmolLM2-360M-Instruct` | ~726 MB | Sub-1B instruct floor | — |
| `gemma3:270m` | `google/gemma-3-270m-it` | ~292 MB | Smallest Gemma 3 text tag on Ollama | — |

### Run command (any row above)

```bash
ollama pull TAG_FROM_TABLE

# Full multilingual suite → English speakable output (leaderboard default)
voxpost summarize speech-check --model TAG_FROM_TABLE --output-lang en

# English fixtures only, French speakable output
voxpost summarize speech-check --model TAG_FROM_TABLE --input-lang en --output-lang fr
```

Tag names are **case-sensitive** and must match `ollama list` exactly (e.g. `qwen3.5:4b`, not `Qwen3.5-4B`).

List fixture input languages and allowed TTS output codes: `voxpost summarize speech-check --list-languages`.

---

## How to contribute a new model

### 1. Pick a model **not already on the leaderboard**

Use the table above or any other **local** tag not listed yet. See [Suggested models to benchmark](#suggested-models-to-benchmark).  
**Do not** submit cloud-only tags (`*:cloud`, remote APIs).

### 2. Run the 24 fixtures

```bash
ollama pull YOUR_MODEL_TAG

# ~/.config/voxpost/voxpost.toml → backend = "ollama", model = YOUR_MODEL_TAG
voxpost summarize speech-check --model YOUR_MODEL_TAG --output-lang en
```

Optional: `--input-lang en` (English fixtures only), `--input-lang fr`, etc. See [SPEECH_CHECK_CONFIG.md](contributing/SPEECH_CHECK_CONFIG.md).

Runs **one fixture at a time** and **auto-creates** a markdown report. After each case:

- Terminal prints `[N/24] case_id — speakable line`
- The report file under `docs/benchmarks/runs/` is updated in place (safe to commit partial runs; **Ctrl+C** keeps what finished)

Use `--no-report` only if you want terminal output without a log file.

#### Required run log filename

Each run gets a unique **run id** (timestamp + random suffix) so the same model can be benchmarked many times without clobbering older logs:

```text
{model}__{backend}__in-{input}__out-{output}__{completed}of{total}__{status}__run-{YYYYMMDD-HHMMSS}-{hex}.md
```

Example (complete 24/24 Ollama run, multilingual input, English output):

```text
qwen3.5-2b__ollama__in-multi__out-en__24of24__complete__run-20260524-143052-a1b2c3.md
```

Partial / stopped early:

```text
qwen3.5-2b__ollama__in-multi__out-en__12of24__stopped-early__run-20260524-143052-a1b2c3.md
```

Override path only if needed: `--report-file path/to/custom.md` (leaderboard PRs should use the auto name).

Use **default mode** (no `--auto-grade`). The markdown report includes metadata, progress table, and per-case speakable lines.

### 3. Score with the chat review prompt

Open **[contributing/MODEL_REVIEW_PROMPT.md](contributing/MODEL_REVIEW_PROMPT.md)** — copy the whole prompt into your judge chat (Claude, ChatGPT, **Composer 2.5**, etc.), then paste the **full markdown report file** underneath.

Record the **judge model name** in the report metadata and PR (e.g. *Judge model: Composer 2.5*).

The chat returns a **PASS / WEAK / FAIL** table and a short verdict. You remain responsible for sanity-checking it before opening a PR.

### 4. Open a PR

Include:

- [ ] New row in the **Leaderboard** table above (sorted correctly) with **Input lang** and **Output lang**
- [ ] Run log: auto-named `docs/benchmarks/runs/{model}__{backend}__in-{input}__out-{output}__{n}of{N}__….md` (with judge grades filled in)
- [ ] **Judge model** named in PR description and report metadata
- [ ] Hardware note (RAM, CPU, GPU, OS) in the PR description
- [ ] Confirm model is **fully local** (Ollama or HF cache on your machine)

Maintainers may re-run a subset before merging.

---

## Add new email fixtures

The suite is **24 cases** today (forwards, invoices, OTP, newsletters, multilingual mail, etc.). If your model fails on a **real production pattern** not covered:

1. Add a JSON fixture in [`src/voxpost/speech_check/fixtures/`](../src/voxpost/speech_check/fixtures/) with:
   - unique `case_id` (filename stem)
   - `"input_lang"` — ISO 639-1 code matching the email body language
   - realistic `event` body (`from_address`, `subject`, `body`)
   - `intent` — what a good speakable line must convey
   - optional `must_mention_any` / `must_not_mention` for `--auto-grade` smoke tests
2. Open a **separate PR** (or combine with a model run if the fixture motivated the test)
3. Re-run affected models after merge (leaderboard may shift)

See [SPEECH_CHECK_CONFIG.md](contributing/SPEECH_CHECK_CONFIG.md) and the call for contributors in [issue #4](https://github.com/omarelkhal/voxpost/issues/4).

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
- [README / config reference](index.md) — configuration reference
