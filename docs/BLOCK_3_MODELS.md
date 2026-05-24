# Block 3 — Summarizer model choice

Voxpost needs a **local, multilingual** summarizer for a **worldwide** product. The shipped default is **`csebuetnlp/mT5_multilingual_XLSum`** (44 languages).

Research method: **web / papers first** → shortlist → **verify each on Hugging Face** against Voxpost constraints below.

---

## Voxpost constraints (scorecard)

| # | Requirement | Must have |
|---|-------------|-----------|
| 1 | **Multilingual** — summarize in the **same language** as the email | Yes |
| 2 | **Local download** — no cloud inference API | Yes |
| 3 | **Short output** — one speakable line (~15–30 words) | Yes |
| 4 | **Transformers** — fits existing Block 3 stack | Strong preference |
| 5 | **Desktop CPU** — shipped desktop app, no GPU assumed | Yes |
| 6 | **Shippable license** — Apache/MIT-style | Yes |
| 7 | **Maintained / proven** — real downloads, model card, benchmarks | Strong preference |

**Reality check:** There is **no** widely adopted, multilingual, **email-specific**, small, local summarizer on Hugging Face. Every option is a tradeoff between **language coverage**, **size/speed**, and **email domain**.

---

## What the web recommends (2024–2025)

| Source / pattern | Recommendation | Fits Voxpost? |
|------------------|----------------|---------------|
| Multilingual summarization papers (XL-Sum, MLSUM, “Towards Unifying Multi-Lingual and Cross-Lingual Summarization”) | **mT5** family fine-tuned on **XL-Sum** or **MLSUM** | Yes — seq2seq, many languages |
| Edge / low-resource NLP surveys | **mT5-small** (~300M) or quantized **mBART** for CPU | Partial — small mT5-XLSum forks exist but quality is poor (see below) |
| Email assistant projects (Vera, E.M.Pilot, local inbox tools) | **Small LLMs** (Qwen2, Gemma, Llama) with prompts | Partial — multilingual + flexible, but causal LM, slower, harder to constrain length |
| Email-specific HF models (wordcab, IrisWiris, 7B email LLMs) | **T5 on email** or **7B instruct** | English-only or too heavy for CPU v1 |
| Microsoft **UniSumm** (ACL 2023) | Unified few-shot summarizer | **English-only** on HF; weights not first-party maintained |

**Web consensus for “many languages + local + summarization”:** mT5-on-XL-Sum, not email-tuned T5.

---

## Hugging Face verification (candidates)

### Tier A — Best fit (recommended)

#### [csebuetnlp/mT5_multilingual_XLSum](https://huggingface.co/csebuetnlp/mT5_multilingual_XLSum)

| Field | Verified on HF |
|-------|----------------|
| **Task** | `summarization` / `text2text-generation` |
| **Base** | `google/mt5-base` (~**580M** params) |
| **Languages** | **44** tagged (fr, en, ar, es, de, pt, hi, ja, zh, tr, ru, vi, …) |
| **Downloads** | **~2.4M** all-time — dominant multilingual summarizer on HF |
| **Training** | XL-Sum (BBC news, 1.35M pairs) — [ACL 2021 paper](https://aclanthology.org/2021.findings-acl.413/) |
| **French XL-Sum ROUGE-1** | **~35.3** (published per-language table) |
| **Output length** | Model config `max_length=84` — good for short cues |
| **API** | `AutoModelForSeq2SeqLM` — drop-in for Voxpost |
| **Input** | Plain article text (no `summarize_brief:` prefix) |
| **License** | Research model; check repo before commercial ship |

**Voxpost fit:** Best match for **worldwide + same-language output + Transformers**. Weak on **email domain** (news-trained) and **CPU latency** (~2–5s).

**Suggested Voxpost prompt shape:**

```text
From: {sender}. Subject: {subject}. {cleaned_body}
```

Generation: `max_length=84`, `num_beams=4`, `no_repeat_ngram_size=2` (from model card).

---

### Tier B — Viable alternatives (not default)

#### [google/flan-t5-base](https://huggingface.co/google/flan-t5-base) (~250M)

| Pros | Cons |
|------|------|
| **58M+** downloads; Apache 2.0; instruction-tuned | Not a dedicated summarizer — needs prompt engineering |
| Tagged **en, fr, de, ro** + “multilingual” | Same-language output **not guaranteed** |
| Smaller / faster than mT5-base XLSum | Weaker than XLSum-finetuned models for summarization |

Example prompt to test: `Summarize this email in the same language as the email:\n{body}`

**Verdict:** Reasonable **fallback** if XLSum is too slow, or for early prototyping — not as reliable for “always French in → French out.”

#### [google/flan-t5-small](https://huggingface.co/google/flan-t5-small) (~80M)

Same tradeoffs as flan-t5-base, faster, lower quality.

#### [Qwen/Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) (~500M)

| Pros | Cons |
|------|------|
| **29+ languages** (per Qwen2.5 paper/blog) | **Causal LM** — new pipeline (chat template, not seq2seq) |
| **43M+** downloads; Apache 2.0 | Easy to ramble; needs strict system prompt + `max_new_tokens` cap |
| Strong for future **“translate to language X”** mode | Slower/heavier than T5-small; CPU marginal |

**Verdict:** Best **Phase 2** candidate for translate-mode + complex instructions — **not** the simplest Block 3 swap.

---

### Tier C — Keep as optional profile

#### [wordcab/t5-small-email-summarizer](https://huggingface.co/wordcab/t5-small-email-summarizer) (~60M)

| Pros | Cons |
|------|------|
| Email-trained; `summarize_brief:` prefix; very fast on CPU | **English only** — confirmed failure on French mail |
| Apache 2.0; already integrated | Wrong default for worldwide product |

**Verdict:** Rejected — English-only; failed on French inbox mail in live tests.

---

### Tier D — Rejected after HF check

| Model | HF finding | Why rejected |
|-------|------------|--------------|
| [ankitkupadhyay/mt5-small-finetuned-multilingual-xlsum](https://huggingface.co/ankitkupadhyay/mt5-small-finetuned-multilingual-xlsum) | ROUGE-1 **~9**; 17 downloads/mo; empty model card | Quality too low |
| [T-Systems-onsite/mt5-small-sum-de-en-v2](https://huggingface.co/T-Systems-onsite/mt5-small-sum-de-en-v2) | DE + EN only | Not worldwide |
| [maan909/unisumm](https://huggingface.co/maan909/unisumm) | **English only**; 7 downloads/mo | Not multilingual on HF |
| [Radiantloom/radiantloom-email-assist-7b](https://huggingface.co/Radiantloom/radiantloom-email-assist-7b) | 7B LLM | Too heavy for CPU v1 |
| [Walid777/llama3-8b-emails-summarization](https://huggingface.co/Walid777/llama3-8b-emails-summarization) | 8B | Too heavy |
| [vapit/bart-large-cnn-finetuned-for-email-and-text](https://huggingface.co/vapit/bart-large-cnn-finetuned-for-email-and-text) | English BART | Not multilingual |
| Per-language `mt5-small-finetuned-xlsum-{lang}` forks | Single language each | Doesn’t scale for “worldwide” one binary |
| [WiseIntelligence/mT5_multilingual_XLSum-Optimum-ONNX-Quantized-AVX2](https://huggingface.co/WiseIntelligence/mT5_multilingual_XLSum-Optimum-ONNX-Quantized-AVX2) | No model card; 6 downloads/mo | Unmaintained; risky |
| GGUF XLSum builds (llama.cpp) | Different runtime | Out of scope until Voxpost adds GGUF path |

---

## Scoring matrix (Voxpost worldwide)

| Model | Multilingual | Email domain | CPU size | Same-lang out | Transformers | HF trust | **Total** |
|-------|:------------:|:------------:|:--------:|:-------------:|:------------:|:--------:|:---------:|
| **mT5_multilingual_XLSum** | ★★★★★ | ★★☆☆☆ | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | **Best default** |
| flan-t5-base (prompted) | ★★★☆☆ | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★★★★★ | ★★★★★ | Fallback |
| Qwen2.5-0.5B-Instruct | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ | ★★★★☆ | ★★☆☆☆ | ★★★★★ | Phase 2 / translate |
| wordcab t5-small | ★☆☆☆☆ | ★★★★☆ | ★★★★★ | ★☆☆☆☆ | ★★★★★ | ★★★★☆ | Rejected (EN-only) |

---

## Decision (updated after deep dive)

### Default for worldwide product

**`csebuetnlp/mT5_multilingual_XLSum`**

Only HF model that clearly checks: **44 languages**, **summarization task**, **millions of downloads**, **published per-language benchmarks**, **short outputs**, **Transformers seq2seq**.

### Config

```toml
[summarize]
model = "csebuetnlp/mT5_multilingual_XLSum"
```

Optional override via `VOXPOST_SUMMARIZER_MODEL` for another compatible seq2seq hub id.

### Pipeline mitigations (still required)

Even with mT5 XLSum:

1. **Keep** `email_clean.py`, `polish_for_tts()`, `is_usable_summary()`, template fallback — news model on forwards/noise will still fail sometimes.
2. **Language detect** → set Supertonic `[tts].lang` (and future `[speech]` mode).
3. **Optional ONNX export** of XLSum later (like Block 4 Supertonic) if CPU latency blocks UX.

---

## Implementation checklist

- [x] Add `[summarize]` to `voxpost.toml` (`model`)
- [x] mT5 XLSum plain-text email input adapter
- [ ] Benchmark French forward mail + English sample on real hardware
- [x] Document download size ~2.3GB and RAM ~2GB+ in BLOCK_3_SUMMARIZE.md

---

## References

- [XL-Sum paper (ACL 2021)](https://aclanthology.org/2021.findings-acl.413/)
- [mT5_multilingual_XLSum model card](https://huggingface.co/csebuetnlp/mT5_multilingual_XLSum)
- [FLAN-T5 paper](https://arxiv.org/abs/2210.11416)
- [Qwen2.5 technical report](https://arxiv.org/abs/2407.10671)
- Supertonic TTS: 31 langs — align `[tts].lang` with summarizer output
