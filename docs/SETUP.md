# Voxpost — full setup guide

Step-by-step setup from zero to **`voxpost listen --speak`**: Google Cloud, Gmail OAuth, Pub/Sub credentials, Ollama, TTS, and `voxpost.toml`.

**Time:** about 30–45 minutes the first time (mostly Google Cloud Console clicks).

**Privacy:** you bring your own GCP project and OAuth client. Voxpost does not bundle cloud credentials, does not store mail bodies, and does not send text to cloud TTS or cloud LLM APIs.

---

## What you are building

```text
Gmail inbox
    → Google Pub/Sub push notification
    → voxpost listen (local daemon)
    → Ollama summarizer (local) → one speakable line
    → Supertonic TTS (local) → chime + spoken briefing
```

Persistent files on disk (only):

| File | Purpose |
|------|---------|
| `~/.config/voxpost/gcp.json` | GCP project, Pub/Sub topic/subscription names |
| `~/.config/voxpost/client_secret.json` | OAuth Desktop client (from Google Cloud Console) |
| `~/.config/voxpost/token.json` | Gmail refresh token (created by `voxpost connect`) |
| `~/.config/voxpost/state.json` | Gmail `historyId` cursor + watch metadata |
| `~/.config/voxpost/voxpost.toml` | Summarizer, TTS, and speech language settings |

Mail content is processed in memory and discarded.

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.11+** | See [RUNTIME.md](RUNTIME.md) |
| **Linux desktop** (recommended) | Audio via PortAudio (`sounddevice`) or `aplay` |
| **Google account** | The Gmail inbox you want to listen to |
| **Google Cloud project** | Free tier is enough for personal use |
| **[gcloud CLI](https://cloud.google.com/sdk/docs/install)** | For `voxpost setup-gcp` and Application Default Credentials |
| **Ollama** | Local summarizer (required for the current recommended path) |
| **Git** | To clone the repo |

Optional but useful: `uv` for faster installs (`pip install uv`).

---

## Step 1 — Clone and install Voxpost

```bash
git clone https://github.com/YOUR_ORG/voxpost.git   # or your fork path
cd voxpost

# Option A: uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,tts]"

# Option B: pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,tts]"
```

Verify the CLI:

```bash
voxpost --help
```

You should see commands including `setup-gcp`, `connect`, `listen`, and `tts`.

---

## Step 2 — Create a Google Cloud project

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project picker (top bar) → **New project**.
3. Name it (e.g. `voxpost-personal`) → **Create**.
4. Select that project in the picker.

Note the **Project ID** (not always the same as the display name). You will use it below as `YOUR_PROJECT_ID`.

---

## Step 3 — Install and log in to gcloud

If `gcloud` is not installed, follow [Google’s install guide](https://cloud.google.com/sdk/docs/install).

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config get-value project    # should print YOUR_PROJECT_ID
```

This login is for **you** running setup commands (`setup-gcp`, enabling APIs). It is separate from the credentials the daemon uses at runtime (Steps 7 and 11).

---

## Step 4 — OAuth consent screen (Gmail read scope)

Google requires a consent screen before you can create an OAuth client.

1. In Cloud Console, go to **APIs & Services** → **OAuth consent screen**.
2. Choose **External** (unless you use a Workspace org with Internal) → **Create**.
3. Fill in **App name** (e.g. `Voxpost`), **User support email**, and **Developer contact email** → **Save and continue**.
4. **Scopes** → **Add or remove scopes** → add:
   - `https://www.googleapis.com/auth/gmail.readonly`
5. **Save and continue**.
6. **Test users** → **Add users** → add the Gmail address you will connect → **Save**.
7. Finish the wizard.

While the app is in **Testing** mode, only listed test users can sign in. That is fine for personal use.

---

## Step 5 — OAuth Desktop client (client_secret.json)

1. Go to **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
2. Application type: **Desktop app**.
3. Name: e.g. `Voxpost desktop`.
4. **Create** → **Download JSON**.

Save the file as:

```bash
mkdir -p ~/.config/voxpost
mv ~/Downloads/client_secret_*.json ~/.config/voxpost/client_secret.json
chmod 600 ~/.config/voxpost/client_secret.json
```

Voxpost also accepts `credentials.json` in the same folder, or `VOXPOST_OAUTH_CLIENT_SECRETS=/path/to/file.json`.

---

## Step 6 — Pub/Sub and Gmail API (automated)

From the repo root, with gcloud logged in and the project set:

```bash
voxpost setup-gcp
```

This command:

- Enables **Gmail API** and **Cloud Pub/Sub API**
- Creates topic `voxpost-gmail` and subscription `voxpost-gmail-pull` (if missing)
- Grants `gmail-api-push@system.gserviceaccount.com` permission to publish to the topic
- Grants **your gcloud user** subscriber on the subscription
- Writes `~/.config/voxpost/gcp.json`

Expected output ends with something like:

```text
GCP setup complete.
  Project:      your-project-id
  Topic:        voxpost-gmail
  Subscription: voxpost-gmail-pull
  ...
```

Custom names:

```bash
voxpost setup-gcp --project YOUR_PROJECT_ID --topic voxpost-gmail --subscription voxpost-gmail-pull
```

---

## Step 7 — Application Default Credentials (Pub/Sub at runtime)

The listen daemon reads Pub/Sub using **Application Default Credentials** (ADC) — not your OAuth Gmail token.

Run once per machine (or when ADC expires):

```bash
gcloud auth application-default login
```

Complete the browser flow. Credentials are stored under `~/.config/gcloud/application_default_credentials.json`.

**Why two logins?**

| Command | Used for |
|---------|----------|
| `gcloud auth login` | Running `setup-gcp` and managing GCP as you |
| `gcloud auth application-default login` | Voxpost **listen** pulling Pub/Sub messages |
| `voxpost connect` | Gmail API (separate OAuth refresh token in `token.json`) |

Optional alternative for servers: a service account key — see [Optional: service account key](#optional-service-account-key-instead-of-adc) below.

---

## Step 8 — Install Ollama

Voxpost’s recommended summarizer path is **Ollama** on your machine (no Hugging Face download step).

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Or follow [ollama.com/download](https://ollama.com/download).

### macOS / Windows

Download the installer from [ollama.com](https://ollama.com).

### Verify

```bash
ollama --version
ollama serve          # usually runs as a service; skip if already running
curl http://localhost:11434/api/tags   # should return JSON (may be empty before pull)
```

---

## Step 9 — Pull a chat model in Ollama

Recommended starting model (good balance of quality and CPU use):

```bash
ollama pull qwen3.5:2b
```

Verify:

```bash
ollama list
# should show qwen3.5:2b
```

Other models work if you set the same name in `voxpost.toml` (`[summarize].model`).

---

## Step 10 — Configure `voxpost.toml`

Create your config directory and copy the example:

```bash
mkdir -p ~/.config/voxpost
cp voxpost.toml.example ~/.config/voxpost/voxpost.toml
```

Edit `~/.config/voxpost/voxpost.toml`. **Minimum for Ollama + speak:**

```toml
[summarize]
backend = "ollama"
model = "qwen3.5:2b"
ollama_host = "http://localhost:11434"

[tts]
model = "supertonic-3"
device = "auto"              # auto | cpu | cuda | gpu
voice = "M1"
lang = "en"
chime_before_speak = true
chime_pause_ms = 350

[speech]
mode = "fixed"
target_lang = "en"           # speakable lines always in English (not email language)
```

### Field reference (common)

| Section | Key | Meaning |
|---------|-----|---------|
| `[summarize]` | `backend` | Must be `ollama` for the Ollama path |
| `[summarize]` | `model` | Ollama model tag (must match `ollama pull …`) |
| `[summarize]` | `ollama_host` | Ollama API URL (default `http://localhost:11434`) |
| `[summarize]` | `idle_unload_minutes` | Minutes before summarizer session is released (Ollama keeps model loaded) |
| `[tts]` | `device` | `auto` picks GPU ONNX when available |
| `[tts]` | `voice` | Supertonic voice id (`M1`–`M5`, `F1`–`F5`) |
| `[speech]` | `target_lang` | Language of spoken briefings (`en`, `fr`, …) |

Environment variables override TOML (see [BLOCK_4_TTS.md](BLOCK_4_TTS.md) and [BLOCK_3_SUMMARIZE.md](BLOCK_3_SUMMARIZE.md)).

**Legacy config:** if you previously used Mailcue, files under `~/.config/mailcue/` are still read when `~/.config/voxpost/` does not exist. Copying to `voxpost/` is recommended.

---

## Step 11 — Download TTS models (Supertonic)

Prefetch ONNX assets (optional but avoids delay on first mail):

```bash
voxpost tts download
```

Test playback:

```bash
voxpost tts test "Voxpost is ready."
```

If you hear nothing, install PortAudio (Linux example):

```bash
# Debian/Ubuntu
sudo apt install libportaudio2
```

Warm up without speaking:

```bash
voxpost tts warmup
```

---

## Step 12 — Connect Gmail (`voxpost connect`)

```bash
voxpost connect
```

This opens a browser OAuth flow. Sign in with the **same Gmail account** you added as a test user on the consent screen.

On success:

```text
Connected as you@gmail.com
Token saved to /home/you/.config/voxpost/token.json
```

Custom callback port if 8765 is busy:

```bash
voxpost connect --port 0
```

---

## Step 13 — Run the full pipeline

```bash
voxpost listen --speak
```

(`--speak` implies `--summarize`.)

You should see:

1. Voxpost ASCII logo and **Starting** panel (mode, model hints)
2. **Listen** panel (account, GCP project, Ollama model, TTS device)
3. `Waiting for new inbox mail…`

Send yourself a test email to the connected inbox. The terminal should show:

- Gmail activity detected
- New message from / subject
- Summarizing (ollama · your-model)
- **Speakable line** (green)
- Speaking aloud → playback finished

### Flags

| Flag | Effect |
|------|--------|
| `--json` | Emit JSON events on stdout (scripting); minimal UI |
| `-v` / `--verbose` | Show detailed module logs |

Stop with **Ctrl+C**.

---

## Step 14 — Sanity checklist

Run through this if something fails:

```bash
# 1. Config files exist
ls -la ~/.config/voxpost/
# expect: client_secret.json, gcp.json, token.json, voxpost.toml

# 2. GCP project
cat ~/.config/voxpost/gcp.json

# 3. Ollama model present
ollama list | grep qwen3.5

# 4. Ollama responds
curl -s http://localhost:11434/api/tags | head

# 5. TTS works
voxpost tts test "Audio check."

# 6. Gmail connected
voxpost connect   # skip if token.json is fresh

# 7. Listen (verbose if needed)
voxpost listen --speak -v
```

---

## Configuration precedence

| Setting | Order (first wins) |
|---------|---------------------|
| GCP project / topic / subscription | `VOXPOST_*` env → `gcp.json` → `gcloud config get-value project` |
| OAuth client JSON | `VOXPOST_OAUTH_CLIENT_SECRETS` → `~/.config/voxpost/client_secret.json` |
| Pub/Sub auth | `VOXPOST_PUBSUB_CREDENTIALS` file → Application Default Credentials |
| Summarizer / TTS / speech | env vars → `voxpost.toml` → built-in defaults |

See also [.env.example](../.env.example) for optional overrides.

---

## Optional: service account key instead of ADC

For a headless server (not typical on a desktop):

```bash
export PROJECT_ID=your-project-id
gcloud iam service-accounts create voxpost-daemon --project="$PROJECT_ID"
gcloud pubsub subscriptions add-iam-policy-binding voxpost-gmail-pull \
  --member="serviceAccount:voxpost-daemon@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber" --project="$PROJECT_ID"
gcloud iam service-accounts keys create voxpost-pubsub-key.json \
  --iam-account=voxpost-daemon@${PROJECT_ID}.iam.gserviceaccount.com
export VOXPOST_PUBSUB_CREDENTIALS="$PWD/voxpost-pubsub-key.json"
```

Gmail OAuth still uses `voxpost connect` (Desktop client + `token.json`).

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| `Missing configuration: GCP project` | Run `voxpost setup-gcp` or set `VOXPOST_GCP_PROJECT` |
| `OAuth client secrets not found` | `client_secret.json` in `~/.config/voxpost/` |
| Pub/Sub / `403` / credential errors | Run `gcloud auth application-default login` |
| `403` on Gmail watch | Rerun `voxpost setup-gcp` (Gmail push SA publisher binding) |
| No Pub/Sub messages | Subscription name in `gcp.json`; subscriber IAM for your ADC identity |
| OAuth `access_denied` / test user | Add your Gmail on OAuth consent screen → Test users |
| `Ollama model … not found` | `ollama pull <model>` matching `[summarize].model` |
| Ollama connection refused | `ollama serve` or install/start Ollama service |
| No audio | `voxpost tts test`; install `libportaudio2`; check volume |
| CUDA TTS not used | Install `onnxruntime-gpu`; set `[tts] device = "gpu"` |
| Duplicate spoken events | Only one `listen` per account; check `state.json` is writable |
| Summaries in wrong language | Set `[speech] mode = "fixed"` and `[speech] target_lang = "en"` |

---

## Quick reference (copy-paste)

After Steps 1–12 once:

```bash
source .venv/bin/activate
voxpost listen --speak
```

First-time ordered commands:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
voxpost setup-gcp
gcloud auth application-default login
# client_secret.json → ~/.config/voxpost/
ollama pull qwen3.5:2b
cp voxpost.toml.example ~/.config/voxpost/voxpost.toml   # edit for ollama backend
voxpost tts download
voxpost connect
voxpost listen --speak
```

---

## Related docs

- [BLOCK_1_GMAIL_EVENTS.md](BLOCK_1_GMAIL_EVENTS.md) — watch / Pub/Sub / history internals
- [BLOCK_3_SUMMARIZE.md](BLOCK_3_SUMMARIZE.md) — summarizer options and QA
- [BLOCK_4_TTS.md](BLOCK_4_TTS.md) — Supertonic settings
- [RUNTIME.md](RUNTIME.md) — Python stack and layout

---

## Before pushing to GitHub

Credentials belong in **`~/.config/voxpost/`**, not in the git repo.

1. Move any OAuth JSON out of the project folder:
   ```bash
   mkdir -p ~/.config/voxpost
   mv client_secret_*.json ~/.config/voxpost/client_secret.json 2>/dev/null || true
   chmod 600 ~/.config/voxpost/client_secret.json
   ```
2. Run the secret check from the repo root:
   ```bash
   bash scripts/check-no-secrets.sh
   ```
3. Review `git status` before every commit — never commit `token.json`, `gcp.json`, `.env`, or `client_secret*.json`.

If a OAuth client secret was ever committed, **rotate it** in Google Cloud Console → Credentials.
