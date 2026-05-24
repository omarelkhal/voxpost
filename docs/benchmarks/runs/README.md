# Speech-check run logs

Contributors attach model run output here when opening a [leaderboard](../MODEL_LEADERBOARD.md) PR.

## Required command

```bash
voxpost summarize speech-check --model YOUR_TAG
```

A markdown report is **created automatically** (one case at a time). Use `--no-report` for terminal-only output.

## Required filename pattern

Each run gets a **unique run id** so repeated tests with the same model never overwrite prior logs:

```text
{model}__{backend}__{completed}of{total}__{status}__run-{YYYYMMDD-HHMMSS}-{hex}.md
```

Examples:

- `qwen3.5-2b__ollama__24of24__complete__run-20260524-143052-a1b2c3.md` — full run
- `qwen3.5-2b__ollama__8of24__stopped-early__run-20260524-143052-a1b2c3.md` — partial (Ctrl+C)

During the run the file **updates in place** (same path until the run finishes). Progress and status live inside the markdown.

Each file includes run metadata, a progress table, and per-case speakable lines. **Grade the markdown** with [MODEL_REVIEW_PROMPT.md](../contributing/MODEL_REVIEW_PROMPT.md) and record the judge model name (e.g. Composer 2.5).

Do not commit logs that include real email addresses from your inbox — the built-in fixtures are synthetic.
