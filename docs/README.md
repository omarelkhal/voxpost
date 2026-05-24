# Voxpost documentation

**Full site (search, dark mode):** [https://omarelkhal.github.io/voxpost/](https://omarelkhal.github.io/voxpost/)

Build locally: `pip install -e ".[docs]"` then `mkdocs serve`.

| Document | Purpose |
|----------|---------|
| [GMAIL_EVENTS_RESEARCH.md](./GMAIL_EVENTS_RESEARCH.md) | OSS landscape and architecture decision |
| [BLOCK_1_GMAIL_EVENTS.md](./BLOCK_1_GMAIL_EVENTS.md) | Block 1 scope, privacy rules, acceptance tests |
| [RUNTIME.md](./RUNTIME.md) | Python stack choice |
| [SETUP.md](./SETUP.md) | Google Cloud and credential setup |
| [BLOCK_3_SUMMARIZE.md](./BLOCK_3_SUMMARIZE.md) | Block 3 local summarization (mT5 XLSum) |
| [BLOCK_3_MODELS.md](./BLOCK_3_MODELS.md) | Multilingual summarizer research & migration plan |
| [BLOCK_4_TTS.md](./BLOCK_4_TTS.md) | Block 4 local TTS (Supertonic 3) |
| [TODO.md](./TODO.md) | Future UI, attachment opt-in, pipeline backlog |

## Changelog

### 0.1.3 — Block 4 TTS

- Block 4 local Supertonic TTS: `voxpost tts test`, `voxpost listen --speak`
- Optional deps: `pip install -e ".[tts]"`

### 0.1.2 — planning

- [TODO.md](./TODO.md) — future desktop UI, attachment opt-in, TTS/email config backlog

### 0.1.1 — gcloud setup

- `voxpost setup-gcp` provisions Pub/Sub and IAM via gcloud CLI
- Config from `~/.config/voxpost/gcp.json` and gcloud project default
- Pub/Sub uses Application Default Credentials (no key file required)

### 0.1.0 — Block 1 scaffold

- Gmail event daemon: `voxpost connect`, `voxpost listen`
- OAuth token + operational state only (no mail storage)
- Pub/Sub streaming pull + `users.watch` + `history.list`
