# Hear what arrived — without opening another tab

**Voxpost** is a local, on-device desktop companion: when mail lands in **Gmail**, you get a **short spoken line** (who, and what it’s about) — not a wall of text and not a cloud TTS API.

<p align="center">
  <img src="assets/voxpost-logo.png" alt="Voxpost" width="480">
</p>

<p align="center">
  <img src="assets/terminal.png" alt="voxpost listen --speak" width="720">
</p>

<p align="center"><em><code>voxpost listen --speak</code> · detect → summarize → speak</em></p>

---

## Why Voxpost?

Many of us **watch the inbox** while coding — tabbing back to Gmail just to see if something matters breaks focus. Voxpost gives you **one actionable sentence**, **on your machine**, when you allow it.

!!! tip "Privacy-first"
    You bring your own Google Cloud project and OAuth credentials. Mail is processed **in memory** and discarded — no archive, no cloud summarizer, no subscription TTS vendor for the core path.

---

## Building blocks

| Block | What | Status |
|-------|------|--------|
| **1** | Gmail OAuth, watch, Pub/Sub, history events | Done |
| **1b** | Attachment metadata (no bytes) | Done |
| **3** | Local summarizer → one speakable line | Done (CLI) |
| **4** | Supertonic 3 on-device TTS | Done (CLI) |
| **5** | Desktop UI + filter rules | Planned |
| **2** | VIP / keyword / quiet-hour rules | Deferred until UI |

<div class="grid cards" markdown>

-   :material-email-fast:{ .lg .middle } **Gmail events**

    ---

    Event-driven pipeline with no mail storage.

    [:octicons-arrow-right-24: Block 1](BLOCK_1_GMAIL_EVENTS.md)

-   :material-brain:{ .lg .middle } **Speakable line**

    ---

    Local chat-LM or seq2seq → intent-first briefing.

    [:octicons-arrow-right-24: Block 3](BLOCK_3_SUMMARIZE.md)

-   :material-volume-high:{ .lg .middle } **Local TTS**

    ---

    Supertonic ONNX on CPU or GPU.

    [:octicons-arrow-right-24: Block 4](BLOCK_4_TTS.md)

-   :material-trophy:{ .lg .middle } **Model leaderboard**

    ---

    Community benchmarks on 24 email fixtures.

    [:octicons-arrow-right-24: Leaderboard](MODEL_LEADERBOARD.md)

</div>

---

## Quick start

=== "Linux / macOS"

    ```bash
    git clone https://github.com/omarelkhal/voxpost.git
    cd voxpost
    python3 -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev,tts]"

    mkdir -p ~/.config/voxpost
    cp voxpost.toml.example ~/.config/voxpost/voxpost.toml
    # Add client_secret.json — see Setup guide

    ollama pull qwen3.5:4b
    voxpost connect
    voxpost listen --speak
    ```

=== "Windows"

    ```powershell
    git clone https://github.com/omarelkhal/voxpost.git
    cd voxpost
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e ".[dev,tts]"

    voxpost connect
    voxpost listen --speak
    ```

Full GCP, OAuth, and Ollama steps: **[Setup guide](SETUP.md)**.

---

## Design principles

1. **Local speech** — notification content for TTS stays on the device.
2. **Short by default** — “Alex says the staging deploy failed,” not the full body.
3. **Silence is a feature** — filter noise; digest mode is a later UX knob.
4. **Gmail proves the loop** — if spoken mail isn’t useful daily, more connectors won’t fix it.
5. **Event-driven, ephemeral** — detect → process → speak → discard.

---

## Next steps

- New here? Read **[Getting started → Overview](getting-started/overview.md)**
- Operator setup: **[Setup (GCP & OAuth)](SETUP.md)**
- Benchmark a model: **[Model leaderboard](MODEL_LEADERBOARD.md)**
- Roadmap: **[TODO](TODO.md)**
