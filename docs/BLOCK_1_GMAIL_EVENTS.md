# Block 1 — Gmail Events

Block 1 proves the first Voxpost building block: **reliable detection of new inbox messages** without storing email content.

Summarization, TTS, UI, and multi-provider connectors are **out of scope** until Block 1 passes acceptance tests.

## Goal

When a new message lands in the user’s Gmail **INBOX**, the local daemon emits exactly **one** ephemeral `NewMailEvent`, logs it to the console, and discards all message content from memory.

## Event shape

```python
@dataclass
class NewMailEvent:
    account_id: str      # Gmail address
    message_id: str
    thread_id: str
    history_id: str
    received_at: str | None  # RFC 2822 Date header when available
```

During development, the daemon prints `from`, `subject`, **`body`** (plain text), and **attachment metadata** to stdout in each JSON event. Message content is **not** written to disk — only emitted on stdout, then discarded from memory.

### Attachment fields (metadata only)

| Field | Type | Description |
|-------|------|-------------|
| `has_attachments` | bool | True when the message has one or more file parts |
| `attachment_count` | int | Number of attachments |
| `attachments` | list | `{filename, mime_type, size_bytes?}` per file — no bytes fetched |

Attachment content is never downloaded in Block 1 (`attachments.get` is not called). A future UI may opt in to feeding attachment text into summarization.

## Architecture

```text
connect  → OAuth → store token in ~/.config/voxpost/
listen   → users.watch(INBOX)
         → Pub/Sub streaming pull
         → history.list(since lastHistoryId)
         → messageAdded → NewMailEvent → stdout → discard
         → renew watch before expiry
```

## Privacy and storage rules

### Allowed on disk

| Data | Location | Purpose |
|------|----------|---------|
| OAuth refresh token | `~/.config/voxpost/token.json` | Re-authenticate without user action |
| `lastHistoryId` | `~/.config/voxpost/state.json` | Dedupe and catch-up after restart |
| Watch expiration / topic | `~/.config/voxpost/state.json` | Renew watch before expiry |
| Filter config (future) | `~/.config/voxpost/config.toml` | VIP rules — not mail content |

### Never persisted in Block 1

- Message subject, body, snippet, sender, or thread history
- Logs containing email content (use message IDs in logs if needed)

## Filters (Block 1 minimum)

- **Label:** `INBOX` only via `users.watch(labelIds=["INBOX"])`.
- **History type:** `messageAdded` only.
- **Exclude:** messages that only appear in `SPAM` or `TRASH` (no cue for label-only moves out of inbox).

## Operational behavior

| Scenario | Expected behavior |
|----------|-------------------|
| New test email arrives | One `NewMailEvent` within a few seconds |
| Daemon restart | No replay of old mail; cursor resumes from `lastHistoryId` |
| Read/archive on another device | No false “new mail” unless a new message arrives |
| Network blip / Pub/Sub reconnect | No duplicate events for the same `messageId` |
| Watch nearing expiry | Daemon renews `watch` automatically |
| Stale `historyId` | Recover once (reset cursor or limited fallback); no storm of old events |
| Pub/Sub notification | Wait ~2 s before `history.list` (indexing race mitigation) |

## Acceptance tests

Run these manually against one Gmail account over several days:

1. **Single event** — Send one email → exactly one console event.
2. **Restart safety** — Restart daemon → send new email → one event; old mail not replayed.
3. **Cross-device** — Archive/read from phone → no spurious event.
4. **Reconnect** — Kill network briefly → reconnect → next mail still works; no duplicates.
5. **Watch renewal** — Leave daemon running past 24 h; watch remains active (check logs for renew).
6. **No content on disk** — Inspect `~/.config/voxpost/` and logs; no subjects or bodies stored.
7. **Spam/trash** — Mail landing only in Spam → no inbox event.

Block 1 is **complete** when these tests are boring and predictable.

## Out of scope

- Summarization or LLM calls
- Local TTS / audio playback
- Desktop UI or system tray
- Multi-account support (single account is fine for Block 1)
- Smart filters (VIP, keywords, quiet hours) — **Block 2, deferred until desktop UI (Block 5)**
- Hosted deployment or multi-tenant OAuth

## CLI (Block 1)

```bash
voxpost connect   # OAuth; stores token
voxpost listen    # watch + Pub/Sub pull + event loop
```

See [SETUP.md](./SETUP.md) for Google Cloud and credential configuration.

## Later blocks

| Block | Scope |
|-------|--------|
| 3 | One-line speakable summary (in memory only) |
| 4 | Local TTS playback |
| 5 | Desktop UI + onboarding (includes Block 2 rule settings) |
| 2 | VIP / keywords / quiet hours — **with Block 5 UI**, not headless |
