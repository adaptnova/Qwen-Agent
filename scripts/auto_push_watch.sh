#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/data/Qwen-Agent}"
REMOTE="${GIT_REMOTE:-novaremote}"
BRANCH="${GIT_BRANCH:-main}"
MSG_PREFIX="auto(nova): sync changes"

cd "$REPO_DIR"

push_once() {
  # Skip if nothing to commit
  if git status --porcelain | grep -q .; then
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    git add -A
    git commit -m "$MSG_PREFIX @ $ts"
    git push "$REMOTE" "HEAD:$BRANCH" || true
  fi
}

if command -v inotifywait >/dev/null 2>&1; then
  # Watch all changes recursively; debounce by sleeping briefly
  inotifywait -mr -e modify,create,delete,move --exclude '\\.git/|__pycache__/' . | while read -r _; do
    sleep 1
    push_once
  done
else
  # Fallback: poll every 10s
  while true; do
    push_once
    sleep 10
  done
fi

