# Voxpost — TODO (future work)

Backlog for features **after Block 1** (Gmail events). Not implemented yet.

---

## Desktop UI (future)

A local desktop app (tray/settings window) for configuration and opt-in behavior. The daemon stays headless; UI talks to it via config files or a local API (TBD).

### Must have (v1 UI)

- [ ] **Connect Gmail** — same OAuth flow as `voxpost connect`, no gcloud for end users
- [ ] **Listen on/off** — start/stop daemon or show status
- [ ] **Supertonic / TTS config** — edit shared TOML (see below); UI is the friendly editor, daemon reads the same file
  - [ ] Voice style (`M1`, `F1`, … — maps to Supertonic `voice_style`)
  - [ ] Language code (`en`, `fr`, … or `na`; may be overridden per-message when language mode is “speak as received”)
  - [ ] Speed, denoising steps (`total_step`), playback device / backend
  - [ ] Optional: volume (if we add gain before playback)
- [ ] **Language mode** *(summarize + TTS — user-configurable in UI)*
  - [ ] **Speak as received** — detect email language locally; summarize/speak in that language (Supertonic `lang` per message; multilingual summarizer or source-language fallback TBD)
  - [ ] **Always in [target language]** — translate/summarize every email into the user’s chosen language before TTS (local models only; no cloud APIs)
  - [ ] Persist choice in shared config (same file/socket as Block 2 rules); daemon reads on each event
  - [ ] Headless v1: optional env vars only until Block 5 ships (e.g. `VOXPOST_SPEECH_LANG_MODE=auto|fixed`, `VOXPOST_SPEECH_TARGET_LANG=fr`)
- [ ] **Shared config file: `~/.config/voxpost/voxpost.toml`**
  - [ ] Single TOML for user-facing settings (UI writes, daemon + CLI read); secrets stay separate (`gcp.json`, `token.json`, OAuth JSON)
  - [ ] **`[tts]`** — Supertonic 3 (mirrors upstream CLI flags where applicable):
    - `voice` — default `M1` (`--voice-style`)
    - `lang` — default `en` (31 codes + `na`; `--lang`)
    - `total_steps` — default `8` (`--total-step`; quality vs latency)
    - `speed` — default `1.05` (`--speed`)
    - `playback` — `sounddevice` | `aplay` | auto
    - `auto_download` — prefetch ONNX on first use (default true)
  - [ ] **`[speech]`** — language mode (see above): `mode = "auto" | "fixed"`, `target_lang = "fr"`, etc.
  - [ ] **`[rules]`** — Block 2 when UI ships (VIP, quiet hours, keywords)
  - [ ] Precedence: env vars override TOML for dev/CI; missing file → built-in defaults (today’s hardcoded Supertonic values)
  - [x] Headless interim (before UI): ship TOML loader + example `voxpost.toml.example`; no interactive editor yet
- [ ] **Email / cue settings** *(Block 2 — implemented with this UI, not before)*
  - [ ] Quiet hours
  - [ ] VIP senders / keywords (what gets spoken)
  - [ ] Ignore newsletters / noise (rules)
- [x] **Attachment awareness (current product decision)**
  - [x] Events expose attachment metadata (names, count, mime, size) — no download
  - [ ] Spoken cue includes attachment presence (Block 3 — in summarizer prompt today)

### Later (UI + opt-in)

- [ ] **Checkbox: “Include attachment in summary”** (per-message or global default)
  - When checked: fetch attachment content in memory → feed into summarizer → TTS → discard
  - When unchecked: awareness only (filename / count), as today
- [ ] Supported attachment types for opt-in summarization (TBD: `.txt` first, then PDF/DOCX with local parsers)
- [ ] Preview last cue / last event (debug, no mail archive)

### Explicitly out of scope for first UI

- Full mail client / inbox browser
- Storing email bodies or attachments on disk
- Cloud TTS or cloud summarization as default
- Per-user GCP / Pub/Sub setup in the UI (operator bundles this in the shipped app)

---

## Pipeline blocks (reference)

| Block | Scope | Status |
|-------|--------|--------|
| 1 | Gmail events (`listen`) | Done |
| 1b | Attachment metadata in events (awareness only) | Done |
| 3 | One speakable line (summarize in memory) | Done (CLI + mT5 XLSum default) |
| 4 | Local TTS playback (Supertonic 3 ONNX) | Done (CLI) |
| 5 | Desktop UI + onboarding | TODO |
| 2 | Rules (VIP, keywords, quiet hours) | **Deferred — needs UI (Block 5)** |

**Block 2 is not built headless.** VIP senders, keywords, quiet hours, and “ignore newsletters” need a settings UI normal users can use. Until Block 5 ships, the pipeline treats **every inbox event** the same: summarize → speak (Blocks 3–4). No interactive rules editor from CLI for now — but a **`voxpost.toml`** for Supertonic/TTS knobs is planned (see Desktop UI → Shared config file).

**Current order:** 1 → 3 → 4 → **5 + 2 together** (UI exposes rule config; daemon reads shared config when present).

---

## Design notes for UI implementer

- **Trust boundary:** Attachment *content* only after explicit user opt-in (checkbox).
- **Ephemeral:** Summaries and fetched attachment text never persisted; same as body today.
- **Normal users:** Never see gcloud, Pub/Sub, or OAuth client JSON — only “Sign in with Google”.
- **Operator:** One GCP project + OAuth app for the product; see [SETUP.md](./SETUP.md).
- **User settings TOML:** `~/.config/voxpost/voxpost.toml` — `[tts]` for Supertonic (voice, lang, speed, steps, playback), `[speech]` for translate vs speak-as-received, `[rules]` for Block 2. UI is the editor; daemon reloads on change (mechanism TBD: SIGHUP, file watch, or restart).

### Example `voxpost.toml` (planned schema)

```toml
[tts]
voice = "M1"
lang = "en"          # or "na"; per-message override when speech.mode = "auto"
total_steps = 8
speed = 1.05
playback = "auto"    # sounddevice | aplay | auto
auto_download = true

[speech]
mode = "auto"        # auto = speak in email language | fixed = always target_lang
target_lang = "fr"   # used when mode = "fixed"
```

---

## Open questions (decide before UI)

- [ ] **Language pipeline:** For “always translate to X”, which local model(s)? (multilingual summarizer vs separate translate step; keep on-device only)
- [x] **Summarizer model (worldwide):** [csebuetnlp/mT5_multilingual_XLSum](https://huggingface.co/csebuetnlp/mT5_multilingual_XLSum) (44 langs) — [BLOCK_3_MODELS.md](./BLOCK_3_MODELS.md)
- [ ] **Language detection:** Library choice for “speak as received” (`langdetect`, `lingua`, etc.) and confidence threshold before falling back to `na` / user default
- [ ] UI stack: Electron, Tauri, or native (GTK/Qt)?
- [ ] Daemon ↔ UI: config file only vs local socket/HTTP?
- [ ] Single-account vs multi-account in v1 UI?
- [x] Which local TTS engine first → **Supertonic 3** ([supertone-inc/supertonic](https://github.com/supertone-inc/supertonic), `pip install supertonic`, ONNX on-device)
