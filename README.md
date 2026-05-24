<p align="center">
  <img src="docs/assets/voxpost-logo.png" alt="Voxpost" width="640">
</p>

**Hear what arrived — without opening another tab.**

Voxpost is a **local, on-device** desktop companion: when something important lands in **Gmail**, you get a **short spoken line** (who, and what it’s about), not a wall of text read aloud and not a cloud text-to-speech API.

<p align="center">
  <a href="docs/assets/terminal.png">
    <img src="docs/assets/terminal.png" alt="voxpost listen --speak in the terminal: VOXPOST banner, config summary, and live pipeline status" width="720">
  </a>
</p>

<p align="center">
  <sub><em><code>voxpost listen --speak</code> · detect → summarize → speak · human-readable log on stderr</em></sub>
</p>

---

## The problem

Many of us **watch the inbox** while coding or deep in another app — tab back to Gmail or notifications just to see if something finished or if a message matters. That breaks focus. Existing “read aloud” tools often **dump too much audio** or send your text to **hosted TTS**.

Voxpost is the opposite: **one actionable sentence**, **on your machine**, when you choose to allow it.

---

## The idea (v1)

| Today | Later (not v1) |
|--------|----------------|
| **Gmail only** | Other sources (RSS, calendar, system notifications, chat apps, …) |

**v1 scope:** personal Gmail → **one speakable line** → local voice synthesis. **Filter rules** (VIP senders, keywords, quiet hours) ship with the **desktop settings UI**, not as a CLI-only block before that.

**Not v1:** WhatsApp/Instagram APIs, multi-OS polish, smart LLM summaries, or replacing your mail client.

---

## Building blocks

Development proceeds in layers. **Block 1** must work before anything else:

| Block | Scope | Status |
|-------|--------|--------|
| **1 — Gmail events** | OAuth, `watch`, Pub/Sub, `history.list` → ephemeral event | Done |
| 1b — Attachments | Metadata only (filenames, count) | Done |
| **3 — Speakable line** | Local summarizer, one sentence, no storage | Done (CLI) |
| **4 — Local TTS** | Supertonic 3 on-device playback | Done (CLI) |
| **5 — Desktop UI** | Connect, listen, TTS + rule settings | Planned |
| 2 — Rules | VIP, keywords, quiet hours | **Deferred until UI (Block 5)** |

Filter rules are **not** a headless milestone — users configure them in the settings UI. Until then, every inbox message can flow through summarize → TTS.

See [docs/BLOCK_1_GMAIL_EVENTS.md](docs/BLOCK_1_GMAIL_EVENTS.md), [docs/BLOCK_3_SUMMARIZE.md](docs/BLOCK_3_SUMMARIZE.md), [docs/BLOCK_4_TTS.md](docs/BLOCK_4_TTS.md), and [docs/GMAIL_EVENTS_RESEARCH.md](docs/GMAIL_EVENTS_RESEARCH.md).

---

## Design principles

1. **Local speech** — notification content used for TTS stays on the device; no subscription TTS vendor required for the core path.
2. **Short by default** — e.g. “Alex says the staging deploy failed,” not the full email body.
3. **Silence is a feature** — newsletters and noise should be filtered; digest mode is a later UX knob.
4. **Gmail proves the loop** — if spoken mail isn’t useful daily, more connectors won’t fix it.
5. **Other services as plugins** — each future source feeds the same “one line to speak” pipeline.
6. **Event-driven, ephemeral** — detect → process in memory → speak → discard; no mail archive.

---

## Privacy-first (open source)

You bring your own credentials — nothing is bundled:

- **Your** Google Cloud project and Pub/Sub (see [docs/SETUP.md](docs/SETUP.md))
- **Your** OAuth Desktop client JSON → `~/.config/voxpost/client_secret.json`
- **Your** Gmail account via `voxpost connect` (refresh token stays local)

---

## Quick start (full pipeline)

See **[docs/SETUP.md](docs/SETUP.md)** for the full step-by-step guide (Google Cloud, OAuth, Ollama, TTS, `voxpost.toml`).

```bash
pip install -e ".[dev,tts]"
gcloud auth login && gcloud config set project YOUR_PROJECT_ID
voxpost setup-gcp
gcloud auth application-default login
# OAuth Desktop JSON → ~/.config/voxpost/client_secret.json  (see SETUP.md)

ollama pull qwen3.5:2b
cp voxpost.toml.example ~/.config/voxpost/voxpost.toml   # set backend = "ollama"
voxpost tts download

voxpost connect
voxpost listen --speak
```

Runtime: **Python 3.11+** ([docs/RUNTIME.md](docs/RUNTIME.md)).

---

## Status

**Blocks 1, 1b, 3, 4:** CLI pipeline (`connect`, `listen --summarize --speak`). **Block 5:** desktop UI planned.

---

## Name

**Voxpost** — *your mail, spoken locally.*
