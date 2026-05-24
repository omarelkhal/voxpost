# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` branch | Yes |
| Older tags / forks | Best effort only |

Voxpost is pre-1.0 desktop software. Install from `main` or the latest release tag when available.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Report privately by opening a GitHub issue with **`[security]`** in the title and asking for a private follow-up, or contact the maintainer through the channel listed on [Buy Me a Coffee](https://buymeacoffee.com/elkhalomar) if you need a direct line.

Include:

- Description of the issue and impact
- Steps to reproduce
- Affected version or commit
- Suggested fix (if you have one)

We aim to acknowledge reports within a few days and will coordinate disclosure once a fix is ready.

## What belongs in a security report

Examples:

- OAuth or token handling that could leak credentials to a third party
- Path traversal or arbitrary file write outside the config directory
- Remote code execution in the daemon or CLI without user intent
- Gmail push / Pub/Sub handling that exposes one user’s mail to another

## What is usually not a vulnerability

- Requiring the user to supply their own Google Cloud project and OAuth client (by design)
- Local summarizer or TTS sending mail text to a **user-configured** local Ollama/HF endpoint on the same machine
- Spoken output of mail the user explicitly chose to listen to
- Missing features (filter rules UI, non-Gmail sources) — file those as normal issues

## Safe disclosure in issues and PRs

Never paste into public threads:

- `client_secret.json`, `token.json`, or refresh tokens
- Full email bodies from real inboxes (use redacted fixtures instead)
- Pub/Sub push payloads containing live message content

Config snippets are welcome if secrets and PII are redacted.

## Dependencies

We depend on Python packages (see `pyproject.toml`), Google Gmail APIs, and optional local ML/TTS runtimes. Keep dependencies updated via PRs; note supply-chain concerns in security reports with reproduction steps.
