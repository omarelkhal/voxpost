# Gmail Events — Open Source Research

This document summarizes how open-source projects detect new Gmail messages and why Voxpost chose its approach.

## The official mechanism

Google does not expose a WebSocket or desktop notification API for third-party mail clients. The supported event path is:

1. **`users.watch`** — register a mailbox (optionally filtered by label, e.g. `INBOX`) with a Cloud Pub/Sub topic.
2. **Pub/Sub notification** — Gmail publishes a small payload when the mailbox changes.
3. **`users.history.list`** — resolve the notification into concrete changes since the last stored `historyId`.
4. **`users.messages.get`** — fetch metadata (From, Subject, snippet) for new message IDs when needed.
5. **Watch renewal** — call `watch` again before expiration (~7 days) or notifications stop.

References:

- [Gmail push notifications](https://developers.google.com/gmail/api/guides/push)
- [users.watch](https://developers.google.com/gmail/api/reference/rest/v1/users/watch)
- [users.history.list](https://developers.google.com/gmail/api/reference/rest/v1/users.history/list)

## Projects evaluated

| Project | License | Activity | Event path | Fit for Voxpost |
|---------|---------|----------|------------|-----------------|
| [gogcli](https://github.com/openclaw/gogcli) | MIT | Active (2026) | `watch` → Pub/Sub push → local HTTP handler → hook URL | **Best behavioral reference** — renewal, stale history recovery, label filters, fetch delay |
| [gmailpush](https://github.com/byeokim/gmailpush) | MIT | Last updated 2023 | `watch` → Pub/Sub push → Express handler → `getMessages()` | Good Node library; assumes public push endpoint |
| [EmailEngine](https://github.com/postalsys/emailengine) | Source-available (paid to run) | Active | `watch` → Pub/Sub → poll subscription → webhooks | Validates production architecture; too heavy for Voxpost core |
| [GmailNotify-PubSub-GCP](https://github.com/Eagnir/GmailNotify-PubSub-GCP) | GPL-3.0 | 2021 | Pub/Sub → Cloud Functions → webhook | Serverless demo, not a local daemon |
| [Realtime-Gmail-Listener](https://github.com/sangnandar/Realtime-Gmail-Listener) | — | Small (2025) | Cloud Run + Apps Script | Wrong shape for on-device TTS |
| **n8n Gmail Trigger** | Fair-code | Active | **Polls** Gmail on an interval | Easy OAuth UX, not true push |
| **IMAP IDLE** (e.g. [mail-listener](https://github.com/patrick095/mail-listener)) | MIT | Various | TCP IDLE on IMAP | Simpler stack, worse consumer UX (app passwords) |

## What OSS converges on

Every serious Gmail **push** implementation uses **`watch` + Pub/Sub + `history.list`**. Polling (n8n) and IMAP IDLE are alternatives but weaker for Voxpost’s goals:

- **Polling** — delayed, quota-heavy, not event-driven.
- **IMAP IDLE** — near real-time but often requires app passwords; OAuth UX is worse for normal users.

## Two delivery patterns for Pub/Sub

| Pattern | Used by | Pros | Cons |
|---------|---------|------|------|
| **Push subscription** → HTTP endpoint | gmailpush, gogcli `watch serve` | Simple request handler | Needs reachable URL (HTTPS or tunnel) |
| **Pull / streaming pull** | EmailEngine, local-agent patterns | No open ports; fits desktop daemon | Long-lived subscriber process |

Voxpost uses **streaming pull** so the daemon runs locally without exposing a webhook.

## Patterns worth copying from gogcli

From [gogcli Gmail watch docs](https://gogcli.sh/watch.html):

- Store only `historyId`, watch expiration, topic, and labels — not mail content.
- Filter to `INBOX`; exclude `SPAM` and `TRASH` by default.
- Restrict history types to `messageAdded` for new-mail detection.
- **Fetch delay** (~2–3 s) after Pub/Sub notification before `history.list` to avoid indexing races.
- **Stale `historyId` recovery** — fall back without replaying the entire mailbox as new events.
- Optional hook payload: `from`, `subject`, `snippet` with body size caps when body is included.

## What Voxpost rejected

- **n8n / Zapier** as the core event layer — polling, external dependency.
- **EmailEngine** as a dependency — full email API platform, paid runtime.
- **IMAP IDLE** for v1 — weaker permission story for non-technical users.
- **Per-user GCP setup** — normal users should only see “Connect Gmail”; the app owner configures Cloud once.

## Voxpost decision

| Layer | Choice |
|-------|--------|
| Detection | Gmail API `users.watch` + Pub/Sub + `users.history.list` |
| Delivery | Pub/Sub **streaming pull** in a local daemon |
| User auth | OAuth 2.0 (`gmail.readonly`) — “Sign in with Google” |
| Operator setup | One GCP project, one topic, OAuth consent screen (app owner) |
| Persistent state | Refresh token + `lastHistoryId` + watch metadata only |
| Runtime | Python (see [RUNTIME.md](./RUNTIME.md)) |

See [BLOCK_1_GMAIL_EVENTS.md](./BLOCK_1_GMAIL_EVENTS.md) for scope and acceptance tests.
