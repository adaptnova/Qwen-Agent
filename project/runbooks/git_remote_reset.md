# Runbook — Git Remote Alignment

## Purpose
Ensure the NovaOps fork always pushes to `https://github.com/adaptnova/Qwen-Agent.git`, even after fresh clones or hard resets.

## Quick Check
```bash
cd /data/Qwen-Agent
git remote -v
```
Expected output:
```
novaremote   https://github.com/adaptnova/Qwen-Agent.git (fetch)
novaremote   https://github.com/adaptnova/Qwen-Agent.git (push)
origin       https://github.com/QwenLM/Qwen-Agent.git (fetch)
origin       https://github.com/QwenLM/Qwen-Agent.git (push)
```

## Realign After Reset
```bash
git remote set-url novaremote https://github.com/adaptnova/Qwen-Agent.git
git branch --set-upstream-to=novaremote/main main
git status -sb
```
`git status -sb` should show `## main...novaremote/main`.

## Fresh Clone Procedure
```bash
git clone https://github.com/adaptnova/Qwen-Agent.git /data/Qwen-Agent
cd /data/Qwen-Agent
git remote add upstream https://github.com/QwenLM/Qwen-Agent.git  # optional reference
git remote rename origin novaremote
git remote add origin https://github.com/QwenLM/Qwen-Agent.git
git branch --set-upstream-to=novaremote/main main
```

## Automation (optional)
Add to `/data/Qwen-Agent/.git/config` under `[remote "novaremote"]` if missing:
```
url = https://github.com/adaptnova/Qwen-Agent.git
pushurl = https://github.com/adaptnova/Qwen-Agent.git
```

## Audit Reminder
- Log every remote change in `project/ops_history.md`.
- Run `git remote -v` weekly (tracked in Ops cadences).
- Before large refactors or git gc, re-run this runbook to confirm alignment.
