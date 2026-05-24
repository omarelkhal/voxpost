# Runtime choice — Python

Voxpost Block 1 uses **Python 3.11+** for the local daemon.

## Why Python

| Factor | Python |
|--------|--------|
| Gmail / Pub/Sub | Official `google-api-python-client` and `google-cloud-pubsub` |
| Local TTS (Block 4) | **Supertonic 3** — `pip install supertonic`, ONNX Runtime, on-device; same family as [Aftertone](https://github.com/omarelkhal/aftertone) |
| Daemon simplicity | Single process, asyncio-friendly Pub/Sub streaming pull |
| Maintainer fit | Small CLI (`connect`, `listen`) without a Node build chain |

Node.js alternatives (`gmailpush`, gogcli patterns) remain valid references; Voxpost does not depend on them.

## Stack (Block 1)

| Package | Role |
|---------|------|
| `google-api-python-client` | Gmail API (`watch`, `history`, `messages`) |
| `google-auth-oauthlib` | OAuth desktop / installed-app flow |
| `google-cloud-pubsub` | Streaming pull subscriber |
| `click` | CLI |

Dependency management: `pyproject.toml` with optional `uv` or `pip install -e .`.

## Layout

```text
src/voxpost/
  cli.py           # connect, listen commands
  oauth.py         # OAuth flow and token storage
  state.py         # lastHistoryId, watch metadata
  events.py        # NewMailEvent
  gmail_watch.py   # watch start / renew / stop
  history.py       # history.list → NewMailEvent list
  pubsub_listener.py  # streaming pull loop
  config.py        # env + paths
  summarize.py     # Block 3 local summarizer
  tts.py           # Block 4 Supertonic speaker
```

Tests live under `tests/` with mocked Gmail and Pub/Sub responses.
