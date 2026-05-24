#!/usr/bin/env bash
# Fail if tracked or staged files look like OAuth tokens / GCP secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail=0

warn() { echo "WARN: $*" >&2; }
die() { echo "ERROR: $*" >&2; fail=1; }

echo "Checking for credential files in repo tree (excluding .venv)…"

while IFS= read -r -d '' f; do
  die "Credential-like file present: $f (move to ~/.config/voxpost/ and ensure .gitignore covers it)"
done < <(
  find . \
    -path './.venv' -prune -o \
    -path './.git' -prune -o \
    \( -name 'client_secret*.json' -o -name 'token.json' -o -name 'gcp.json' -o -name 'state.json' -o -name '*-pubsub-key.json' -o -name '.env' \) \
    -print0 2>/dev/null
)

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Checking git index for forbidden paths…"
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    die "Forbidden path staged or tracked: $path"
  done < <(
    git ls-files -z 2>/dev/null | tr '\0' '\n' | grep -E \
      '(client_secret|credentials\.json|token\.json|gcp\.json|state\.json|\.env$|pubsub-key\.json)' || true
  )
fi

echo "Scanning source tree for leaked OAuth secret patterns…"
if rg -n --glob '!.venv/**' --glob '!.git/**' --glob '!uv.lock' \
  'GOCSPX-[A-Za-z0-9_-]{10,}|"refresh_token"\s*:\s*"[^"]+"' . >/dev/null 2>&1; then
  die "Possible secret material in tracked files — run: rg 'GOCSPX-|refresh_token' ."
fi

if [[ "$fail" -ne 0 ]]; then
  echo >&2
  echo "Fix the issues above before git add / git push." >&2
  exit 1
fi

echo "OK — no obvious secrets in the repo tree."
