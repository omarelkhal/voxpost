# Contributing to Voxpost

Thanks for helping make **local, private “hear what arrived”** work for more people.

Voxpost is **free and open source** — no paywall, no catch. Contributions (code, docs, benchmarks, fixtures, bug reports) are how we give back together.

## Community

- This project follows the **[Code of Conduct](CODE_OF_CONDUCT.md)**. By participating, you agree to uphold it.
- **Issues:** use [GitHub Issues](https://github.com/omarelkhal/voxpost/issues) and pick a template when it fits (**Model speech-check benchmark**, **Multilingual fixture**, or a plain bug/feature issue).
- **Security:** see **[SECURITY.md](SECURITY.md)** — do not paste OAuth tokens, refresh tokens, or mail content in public issues.

## What we’re building

| Area | Status | Help wanted |
|------|--------|-------------|
| **Gmail events** (watch, Pub/Sub, history) | Done (CLI) | Edge cases, docs |
| **Speakable line** (local summarizer) | Done (CLI) | Quality, new models on leaderboard |
| **Local TTS** (Supertonic 3) | Done (CLI) | GPU docs, Windows/macOS audio |
| **Desktop UI** (connect, listen, rules) | Planned | Design feedback, later PRs |
| **Filter rules** (VIP, quiet hours) | Deferred until UI | Not headless CLI config for v1 |

## Principles

- **Privacy first:** mail is processed in memory → speak → discard; no mail archive in v1.
- **Local by default:** summarizer and TTS run on your machine; no cloud inference or cloud TTS in the core path.
- **One speakable line:** brief for short mail, descriptive for long mail — intent-first briefings, not neutral dumps.
- **Silence is a feature:** newsletters and noise should be filtered (rules ship with the desktop UI).
- **Community benchmarks:** compare models on the **same 24 fixtures** — do not overfit prompts to a tiny subset.

## Dev setup

```bash
git clone https://github.com/omarelkhal/voxpost.git
cd voxpost
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,tts]"
```

Optional for daily testing: [Ollama](https://ollama.com), GCP + OAuth per [docs/SETUP.md](docs/SETUP.md).

Run tests:

```bash
pytest
```

## Ways to contribute

### Model leaderboard (high impact, no Gmail needed)

1. Pick a **local** model not on [docs/MODEL_LEADERBOARD.md](docs/MODEL_LEADERBOARD.md).
2. Run `voxpost summarize speech-check --model YOUR_TAG` (writes under `docs/benchmarks/runs/`).
3. Grade the markdown report with [docs/contributing/MODEL_REVIEW_PROMPT.md](docs/contributing/MODEL_REVIEW_PROMPT.md) (name the judge model).
4. Open a PR: leaderboard row + the graded run log.

Use the **Model speech-check benchmark** issue template to track your run.

### New speech-check fixtures

Add diverse, realistic cases to the fixture set (see [docs/contributing/SPEECH_CHECK_CONFIG.md](docs/contributing/SPEECH_CHECK_CONFIG.md)). Use the **Multilingual fixture** issue template or a PR with a short rationale.

### Code and docs

- Keep PRs focused; match existing style in the touched module.
- Update docs when CLI flags, config keys, or setup steps change.
- Block 3 QA: manual `speech-check` on the full fixture set before claiming summarizer work is done; `--auto-grade` is CI-only.

## Pull requests

- Fill out the [pull request template](.github/PULL_REQUEST_TEMPLATE.md).
- Link related issues when applicable.
- For summarizer or speakable-line changes, note whether you ran `speech-check` and on which model.

Maintainers review when they can. **Optional support:** if Voxpost helps you, [buy me a coffee](https://buymeacoffee.com/elkhalomar) — never required for using or contributing.

## Questions

Open a [GitHub Discussion](https://github.com/omarelkhal/voxpost/discussions) or an issue with context (OS, Python version, config redacted). Do not attach real mail bodies or credentials.
