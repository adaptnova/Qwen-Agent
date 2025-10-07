# Ops Review Cadence — Weekly Checklist

## Purpose
Keep NovaOps infrastructure aligned by auditing critical services and configuration each week. Reviews run every **Monday 17:00 UTC** (or next business day).

## Pre-Review Prep
- Pull latest `main` from `https://github.com/adaptnova/Qwen-Agent.git`.
- Read `project/ops_history.md` for outstanding follow-ups.
- Ensure `/data/secrets/dbops_connections_guide.md` is up to date if new services were added.

## Weekly Checklist
1. **Git Remote Audit**
   ```bash
   cd /data/Qwen-Agent
   git remote -v
   ```
   - Confirm `novaremote` points to `https://github.com/adaptnova/Qwen-Agent.git`.
   - If out of sync, follow `project/runbooks/git_remote_reset.md`.

2. **Repo Drift & Pending Pushes**
   ```bash
   git status -sb
   git log novaremote/main..main --oneline
   ```
   - Resolve unpushed changes or open PRs.

3. **Database Health Checks**
   - Run Redis and Postgres checks from `/data/secrets/dbops_connections_guide.md`.
   - Note anomalies in `project/ops_history.md`.

4. **MLflow Tracker**
   - Verify `mlflow.service` status and TLS/SSO front-end availability.
   - Confirm tracking URI reachable from Nova control host.

5. **Ray Serve / Model Fleet**
   - Review status of Ray Serve deployments (generalist, coder, thinker).
   - Capture outstanding actions for Forge in `project/requests`.

6. **Systemd Services**
   ```bash
   systemctl --failed
   journalctl -u nova-agent -n 200 --no-pager
   ```
   - Ensure `nova-agent`, `nova-control`, `nova-devtools-mcp`, and `nova-watchdog` are healthy.

7. **Backlog & Requests**
   - Review `project/requests/*.md` for open items (Forge, PlatformOps).
   - Update statuses or escalate blockers to Chase/Forge.

## Review Output
- Append conclusions and issues to `project/ops_history.md` with timestamp.
- Open new requests/runbooks as needed for follow-ups.

## Points of Contact
- Chase (NovaOps Lead) — chase@novaops.internal
- Atlas (NovaOps) — atlas@novaops.internal
- Forge (PlatformOps) — forge@novaops.internal
