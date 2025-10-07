# Nova Deployment Guide

This guide describes how to deploy the Nova agent on an Ubuntu 24.04 host with root access and a persistent `/data` volume.

## 1. Prerequisites

- Ubuntu 24.04 (root)
- Python 3.10+
- Git, curl, systemd (default on Ubuntu)
- Network egress to:
  - vLLM endpoint (`http://10.0.1.1:18000/v1` by default)
  - Serper/Tavily APIs (if used)
  - Target databases/search backends

## 2. Clone & Dependencies

```bash
git clone https://github.com/adaptnova/Qwen-Agent.git /data/Qwen-Agent
cd /data/Qwen-Agent
pip install -r requirements-nova.txt
```

## 3. Workspace & Secrets

```bash
sudo mkdir -p /data/nova/{logs,runs,tools,datasets,tmp,caches}
sudo mkdir -p /data/secrets
sudo chown -R $(whoami):$(whoami) /data/nova /data/secrets
```

Create secret files (examples):

`/data/secrets/SERPER.env`
```
SERPER_API_KEY=...
SERPER_URL=https://google.serper.dev/search
```

`/data/secrets/TAVILY.env`
```
TAVILY_API_KEY=...
```

`/data/secrets/POSTGRES_MAIN.env`
```
PGHOST=...
PGPORT=5432
PGUSER=...
PGPASSWORD=...
PGDATABASE=...
```

Repeat for CLICKHOUSE_MAIN.env, NEO4J_MAIN.env, WEAVIATE_MAIN.env, MEILI_MAIN.env, etc.

## 4. Systemd Services

Copy unit files and enable:

```bash
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nova-watchdog.service
sudo systemctl enable --now nova-repo-autopush.service
sudo systemctl enable --now nova-devtools-mcp.service
sudo systemctl enable --now nova-agent.service
sudo systemctl enable --now nova-control.service
sudo systemctl enable --now nova-cleanup.timer
```

Optional: configure `vllm@.service` drop-ins if hosting vLLM locally.

## 5. Logrotate

```bash
sudo cp ops/logrotate/nova /etc/logrotate.d/nova
```

## 6. Housekeeping

Daily cleanup runs via `nova-cleanup.timer`. Adjust TTL via `NOVA_CLEAN_TTL_DAYS` env if needed.

## 7. (Optional) Qwen3-Coder Specialist

1. Provision a separate vLLM endpoint for the coder model (e.g., `NOVA_CODER_LLM_SERVER=http://<host>:8010/v1`).
2. Export coder env vars:
   ```bash
   export NOVA_CODER_LLM_SERVER=http://127.0.0.1:8010/v1
   export NOVA_CODER_LLM_MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
   ```
3. Use `examples/nova_router.py` to route code-heavy tasks:
   ```bash
   python examples/nova_router.py "Refactor this Python class to use dependency injection"
   ```
4. Control plane integration (soon): update `nova_control_server` to swap in the router once the coder endpoint is stable.

## 7. Validation

```bash
export QWEN_AGENT_DEFAULT_WORKSPACE=/data/nova
python scripts/nova_healthcheck.py --json
```

Expected output: `{"ok": true, ...}`. Non-zero exit indicates an issue.

Manual checks:
- `journalctl -u nova-agent -f`
- `curl http://127.0.0.1:7125/health`
- `printf 'STOP' | socat - UNIX-CONNECT:/run/nova_watchdog.sock` (kill switch)
- `ls /data/nova/logs/transcript-*.jsonl`
- `python scripts/nova_router.py` (quick sanity check once coder endpoint is available)

## 8. Auto Push

The repo monitors for changes and pushes to `novaremote` automatically. Configure Git remote if not already:
```bash
git remote add novaremote https://github.com/adaptnova/Qwen-Agent.git
```

## 9. Optional

- Update `/data/nova/mcp.json` (copy from `examples/mcp.dev.json`) for Chrome DevTools MCP integration.
- Customize environment in `/data/secrets/nova.env` loaded by systemd units.

## 10. Handoff Checks

- `nova_healthcheck` passes
- `/status` shows queue length and background jobs
- `/enqueue` and `/tasks` operate (jobs complete with redacted results)
- Transcripts populate `/data/nova/logs`
- Logrotate rotates when files exceed 50MB
- Cleanup timer removes tmp artifacts older than 14 days

Once all checks pass, Nova is production-ready. For multi-model deployments, validate each specialist endpoint separately.
