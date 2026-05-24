# Overview

Voxpost connects **Gmail push notifications** to a **local speakable-line pipeline** and **on-device TTS**. v1 is CLI-only; a desktop UI is planned (Block 5).

## What you need

| Piece | Purpose |
|-------|---------|
| **Google Cloud project** | Pub/Sub topic + subscription for Gmail watch |
| **OAuth Desktop client** | `voxpost connect` — refresh token stays local |
| **Ollama** (recommended) | Local summarizer (`qwen3.5:4b`, `phi4-mini`, …) |
| **Supertonic 3** | Local TTS (`voxpost tts download`) |

Nothing is bundled — you bring your own credentials. See **[Setup](../SETUP.md)**.

## End-to-end flow

```mermaid
flowchart LR
  Gmail -->|watch + Pub/Sub| Daemon
  Daemon -->|history.list| Event[New mail event]
  Event --> Summarize[Local summarizer]
  Summarize --> Line[Speakable line]
  Line --> TTS[Supertonic TTS]
  TTS --> Speaker[Your speakers]
```

1. **`voxpost connect`** — OAuth; stores refresh token in `~/.config/voxpost/`.
2. **`voxpost listen --speak`** — subscribes to Pub/Sub, fetches new messages via Gmail API, summarizes in memory, speaks, discards.
3. **No mail archive** — only OAuth token + `lastHistoryId` persist.

## CLI commands

| Command | Description |
|---------|-------------|
| `voxpost setup-gcp` | One-time Pub/Sub + IAM (operator) |
| `voxpost connect` | Gmail OAuth |
| `voxpost listen` | Event daemon (log only) |
| `voxpost listen --summarize` | + local speakable line on stderr |
| `voxpost listen --speak` | + Supertonic playback |
| `voxpost summarize speech-check` | 24-fixture quality benchmark |
| `voxpost tts download` / `tts test` | Prefetch and test audio |

## Configuration

Settings live in **`~/.config/voxpost/voxpost.toml`**:

```toml
[summarize]
backend = "ollama"
model = "qwen3.5:4b"
ollama_host = "http://localhost:11434"

[tts]
model = "supertonic-3"
device = "auto"
lang = "en"

[speech]
mode = "fixed"
target_lang = "en"
```

**Speech language** comes from TOML only — never inferred from the email body. For benchmarks you can override with `--input-lang` and `--output-lang`; see **[Speech-check languages](../contributing/SPEECH_CHECK_CONFIG.md)**.

## Platform notes

- **Linux** — best tested; PortAudio or `aplay` for playback.
- **macOS** — Ollama may use Metal; TTS usually CPU ONNX.
- **Windows** — config under `%USERPROFILE%\.config\voxpost\`.

Details: **[Runtime](../RUNTIME.md)**, **[Setup](../SETUP.md)**, **[Block 4 TTS](../BLOCK_4_TTS.md)**.

## What’s not in v1

- Desktop settings UI (Block 5)
- Headless filter rules (Block 2 — deferred until UI)
- Attachment bytes to summarizer (metadata only today)
- Non-Gmail sources (future plugins)

See **[Roadmap](../TODO.md)**.
