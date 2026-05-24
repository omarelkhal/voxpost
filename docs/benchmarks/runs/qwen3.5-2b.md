# Speech-check benchmark — `qwen3.5:2b`

Incremental run log for the [community leaderboard](../../MODEL_LEADERBOARD.md). This file updates **after each case**; commit partial progress or stop with Ctrl+C.

## Run metadata

| Field | Value |
|-------|-------|
| Model | `qwen3.5:2b` |
| Backend | ollama |
| Host | Linux x86_64, x86_64 |
| Started (UTC) | 2026-05-24 02:54 |
| Status | **complete** (1/1 cases) |
| Judge model | *(pending — paste into MODEL_REVIEW_PROMPT.md)* |

## Progress

| # | case_id | label | speakable line | judge grade |
|---|---------|-------|----------------|-------------|
| 1 | `en_short_ack` | English — short acknowledgment | You received an email from Jordan Lee at team saying three p.m. tomorrow works for him. | *(pending)* |

## Cases

### 1/1 `en_short_ack`

- **Label:** English — short acknowledgment
- **Intent:** Quick thanks and confirm 3pm meeting.
- **From:** Jordan Lee <jordan@team.io>
- **Subject:** Re: sync

**Body preview**

```
Thanks — 3pm tomorrow works for me.
```

**Model speakable line**

> You received an email from Jordan Lee at team saying three p.m. tomorrow works for him.

**Judge grade:** *(pending)* — use [MODEL_REVIEW_PROMPT.md](../../contributing/MODEL_REVIEW_PROMPT.md)

## Next steps

1. Paste this file (or the terminal log) into a chat with the community review prompt.
2. Fill **judge grade** column and per-case grades (PASS / WEAK / FAIL).
3. Open a PR updating `docs/MODEL_LEADERBOARD.md` with totals and this run log.
