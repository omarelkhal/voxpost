# Block 3 — Local summarization

Block 3 turns a **Block 1 `NewMailEvent`** into a **`SummarizedMailEvent`**: same mail fields plus one **`speakable_line`** for TTS (Block 4). Everything stays in memory; no cloud summarization API.

## Model

- **[csebuetnlp/mT5_multilingual_XLSum](https://huggingface.co/csebuetnlp/mT5_multilingual_XLSum)** (~580M params, 44 languages)
- Summarizes in the **source language** (plain text: `From`, `Subject`, body)
- Runs locally via `transformers` on CPU
- Download ~2.3 GB; expect ~2 GB+ RAM at inference

Configure in `~/.config/voxpost/voxpost.toml`:

```toml
[summarize]
model = "csebuetnlp/mT5_multilingual_XLSum"
```

Override once: `VOXPOST_SUMMARIZER_MODEL=…` (any compatible seq2seq hub id).

See [BLOCK_3_MODELS.md](./BLOCK_3_MODELS.md) for why this model was chosen.

## Install

```bash
pip install -e ".[summarize]"
voxpost summarize download
```

Model files land under `~/.config/voxpost/models/mT5_multilingual_XLSum/`.

## Test (sample event)

```bash
voxpost summarize test
voxpost summarize test --show-input
```

## Test (real event JSON from `voxpost listen`)

```bash
# Terminal 1
voxpost listen

# Copy one JSON line, then:
voxpost summarize test --event-json '{"account_id":"...", ...}'
```

Or save a line to `event.json` and:

```bash
voxpost summarize test --file event.json
```

Output is **SummarizedMailEvent JSON** — all mail fields plus `speakable_line`.

## Listen with summarization

```bash
voxpost listen --summarize
```

Each new inbox message prints summarized JSON instead of raw `NewMailEvent`.

## Privacy

- Model downloaded once; inference is local only
- Set `HF_HUB_OFFLINE=1` after download for fully offline runs
- No email content sent to Hugging Face Inference API

## Pipeline

```text
NewMailEvent → build_model_input() → mT5 XLSum → polish_for_tts() → speakable_line → SummarizedMailEvent
```

Block 4 (local TTS) consumes `speakable_line` only.

### Speakable polish (TTS-friendly output)

Voxpost makes output speakable in three steps:

1. **Body cleaning** — `clean_email_body()` strips forward wrappers, signatures, URLs, and legal disclaimers before the model runs.
2. **Post-processing** — `polish_for_tts()` expands day codes (`JEU` → `jeudi`, `Wed` → `Wednesday`), email shorthand (`mtg`, `tmrw`, `pls`), and symbols (`&`, `%`).
3. **Quality gate** — `is_usable_summary()` rejects weak or meta-echo lines; template fallback uses the cleaned body.

Set locale for expansion tables:

```bash
export VOXPOST_SPEAKABLE_LANG=all   # default — English + French day codes
export VOXPOST_SPEAKABLE_LANG=fr    # French day codes only
export VOXPOST_SPEAKABLE_LANG=en    # English only
```

**Block 2 (rules)** is not implemented yet. VIP senders, keywords, and quiet hours need the **desktop settings UI (Block 5)** — until then, every inbox event may be summarized and spoken.
