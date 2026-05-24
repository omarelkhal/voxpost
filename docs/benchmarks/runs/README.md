# Speech-check run logs

Contributors attach model run output here when opening a [leaderboard](../MODEL_LEADERBOARD.md) PR.

```bash
voxpost summarize speech-check --model YOUR_TAG --workers 1 \
  | tee docs/benchmarks/runs/YOUR_TAG.txt
```

One file per model tag. Do not commit logs that include real email addresses from your inbox — the built-in fixtures are synthetic.
