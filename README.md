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
- **Your** OAuth Desktop client JSON (path below)
- **Your** Gmail account via `voxpost connect` (refresh token stays local)

| Platform | Config directory |
|----------|------------------|
| **Linux** | `~/.config/voxpost/` |
| **macOS** | `~/.config/voxpost/` |
| **Windows** | `%USERPROFILE%\.config\voxpost\` (same as `~/.config/voxpost/` in Python) |

Files: `client_secret.json`, `gcp.json`, `token.json`, `voxpost.toml` — see [docs/SETUP.md](docs/SETUP.md) for GCP and OAuth setup (same in the browser on every OS).

---

## Configuration by platform

**Same everywhere:** Google Cloud + OAuth (browser), **`voxpost.toml`** (Ollama + local TTS), `voxpost connect`, `voxpost listen --speak`.  
**Differs by OS:** install commands, virtualenv activation, and audio dependencies.

Full GCP/OAuth walkthrough: **[docs/SETUP.md](docs/SETUP.md)**.

### Shared `voxpost.toml`

Copy the example into your config dir on every platform, then edit if needed:

```toml
[summarize]
backend = "ollama"
model = "qwen3.5:2b"
ollama_host = "http://localhost:11434"

[tts]
model = "supertonic-3"
device = "auto"       # linux: cuda/cpu · macOS: often cpu · windows: cuda/cpu
voice = "M1"
lang = "en"

[speech]
mode = "fixed"
target_lang = "en"
```

---

### Linux

**Best tested.** Debian/Ubuntu-style example; adapt package names for Fedora, Arch, etc.

**Prerequisites**

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git libportaudio2
# gcloud: https://cloud.google.com/sdk/docs/install#linux
# Ollama: curl -fsSL https://ollama.com/install.sh | sh
```

**Install Voxpost**

```bash
git clone https://github.com/omarelkhal/voxpost.git
cd voxpost
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,tts]"
```

**Config paths**

```bash
mkdir -p ~/.config/voxpost
chmod 700 ~/.config/voxpost
# OAuth Desktop JSON from Google Cloud Console:
cp ~/Downloads/client_secret_*.json ~/.config/voxpost/client_secret.json
chmod 600 ~/.config/voxpost/client_secret.json
cp voxpost.toml.example ~/.config/voxpost/voxpost.toml
```

**GCP, Ollama, TTS, run** (after [SETUP.md](docs/SETUP.md) Steps 2–10)

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
voxpost setup-gcp
gcloud auth application-default login

ollama pull qwen3.5:2b
voxpost tts download
voxpost tts test "Linux audio check."

voxpost connect
voxpost listen --speak
```

**Linux TTS notes:** `[tts] playback = "auto"` uses PortAudio (`sounddevice`) or `aplay`. For NVIDIA GPU TTS, install CUDA + `onnxruntime-gpu`, then set `[tts] device = "gpu"`.

---

### macOS

**Prerequisites** (Homebrew)

```bash
brew install python@3.11 git portaudio ollama
brew install --cask google-cloud-sdk   # or: https://cloud.google.com/sdk/docs/install#mac
```

**Install Voxpost**

```bash
git clone https://github.com/omarelkhal/voxpost.git
cd voxpost
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,tts]"
```

**Config paths**

```bash
mkdir -p ~/.config/voxpost
chmod 700 ~/.config/voxpost
cp ~/Downloads/client_secret_*.json ~/.config/voxpost/client_secret.json
chmod 600 ~/.config/voxpost/client_secret.json
cp voxpost.toml.example ~/.config/voxpost/voxpost.toml
```

**GCP, Ollama, TTS, run**

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
voxpost setup-gcp
gcloud auth application-default login

ollama pull qwen3.5:2b
# Start Ollama if not running: open the Ollama app or `ollama serve`
voxpost tts download
voxpost tts test "macOS audio check."

voxpost connect
voxpost listen --speak
```

**macOS notes:** Summarizer runs via Ollama (Metal when Ollama uses it). Supertonic TTS is ONNX — `[tts] device = "auto"` usually picks **CPU**; that is normal. Allow microphone/speaker access if macOS prompts during `tts test`.

---

### Windows

**Prerequisites**

- [Python 3.11+](https://www.python.org/downloads/) — enable **“Add python.exe to PATH”**
- [Git for Windows](https://git-scm.com/download/win)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install#windows)
- [Ollama for Windows](https://ollama.com/download/windows)

**Install Voxpost** (PowerShell)

```powershell
git clone https://github.com/omarelkhal/voxpost.git
cd voxpost
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,tts]"
```

**Config paths** (PowerShell)

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\voxpost"
Copy-Item "$env:USERPROFILE\Downloads\client_secret_*.json" "$env:USERPROFILE\.config\voxpost\client_secret.json"
Copy-Item voxpost.toml.example "$env:USERPROFILE\.config\voxpost\voxpost.toml"
```

**GCP, Ollama, TTS, run** (Command Prompt or PowerShell)

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
voxpost setup-gcp
gcloud auth application-default login

ollama pull qwen3.5:2b
voxpost tts download
voxpost tts test "Windows audio check."

voxpost connect
voxpost listen --speak
```

**Windows notes:** Voxpost reads config from `%USERPROFILE%\.config\voxpost\`. OAuth opens your default browser; allow the localhost callback. For GPU TTS, install NVIDIA drivers + CUDA-compatible `onnxruntime-gpu` if you use `[tts] device = "gpu"`. If audio fails, try `[tts] playback = "sounddevice"` in `voxpost.toml`. **WSL2 (Ubuntu)** is an alternative — follow the **Linux** steps inside WSL if you prefer a Unix-like environment.

---

## Quick reference

| Step | Command (any OS, venv active) |
|------|-------------------------------|
| Prefetch TTS | `voxpost tts download` |
| Test audio | `voxpost tts test "Hello."` |
| Link Gmail | `voxpost connect` |
| Run pipeline | `voxpost listen --speak` |

Runtime: **Python 3.11+** ([docs/RUNTIME.md](docs/RUNTIME.md)).

---

## Status

**Blocks 1, 1b, 3, 4:** CLI pipeline (`connect`, `listen --summarize --speak`). **Block 5:** desktop UI planned.

---

## Name

**Voxpost** — *your mail, spoken locally.*
