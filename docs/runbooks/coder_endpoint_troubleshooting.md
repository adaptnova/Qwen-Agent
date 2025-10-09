# Coder Endpoint Troubleshooting

Use this guide when the coder service fails validation or exhibits degraded behaviour. Triage from symptoms to resolution, then log the outcome in `project/ops_history.md`.

---

## 1. Quick Diagnostics

| Command | Expected Result | Notes |
|---------|-----------------|-------|
| `curl -sS http://127.0.0.1:18000/v1/models` | JSON listing with `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` | Tests proxy + vLLM |
| `curl -sS http://127.0.0.1:18010/v1/models` | Same as above | Tests vLLM directly |
| `ss -ltnp | grep 18010` | Listen socket owned by `python … vllm` | Confirms service alive |
| `tail -n 100 /data/dev-vllm/reports/logs/vllm_coder_server.log` | No stack traces | Inspect on failure |
| `ps -ef | grep socat` | Forwarder process present | 18000 proxy |

---

## 2. Symptom → Root Cause Matrix

### A. Garbled / Non-English Output
- **Cause:** Missing or incorrect tool parser.
- **Fix:** Restart vLLM with `--tool-call-parser qwen3_coder --enable-auto-tool-choice`. Ensure vLLM ≥ 0.10.1.1 (patches the Qwen3-Coder parser RCE).

### B. No `tool_calls` in responses
- **Cause:** Function calling disabled or agent templating interfering.
- **Fix:** Confirm launch flags above, verify clients use **Native** function calling, and ensure `generate_cfg.use_raw_api=True` in Qwen-Agent.

### C. HTTP 404 / 502 / timeouts
- **Cause:** Proxy crashed or vLLM down.
- **Fix:** Restart socat (`socat TCP-LISTEN:18000,reuseaddr,fork TCP:127.0.0.1:18010`), or bind clients directly to 18010 temporarily.

### D. `system_shell` / `write_file` failures (phase A)
- **Cause:** Insufficient permissions.
- **Fix:** Run Qwen-Agent under the ops user with sudo rights, or adjust workspace paths. Ensure no restrictive SELinux/AppArmor profiles block writes.

### E. `code_interpreter` kernel crash
- **Cause:** Missing extras or kernel state from previous runs.
- **Fix:** `pip install -U "qwen-agent[code_interpreter]"`, clean `/tmp/qwen_code_interpreter*`, restart the agent.

### F. Serper / web tool failures
- **Cause:** Missing API key env vars.
- **Fix:** Configure the relevant secrets (`/data/secrets/SERPER.env`) and source into the agent environment.

### G. SQL tool refuses connection
- **Cause:** No database service.
- **Fix:** Provide a valid profile via secrets (e.g., `/data/secrets/POSTGRES_MAIN.env`) or ignore if unused.

### H. “Tool not registered”
- **Cause:** Tool registry not initialized before running assistant.
- **Fix:** Confirm imports from `qwen_agent.tools` or that custom tools are decorated with `@register_tool` before agent instantiation.

---

## 3. Restart Procedures

### vLLM Service
```bash
sudo systemctl restart vllm-coder.service   # if configured under systemd
# or manually:
pkill -f "vllm.entrypoints.openai.api_server"
# rerun launch command (see setup runbook)
```

### socat Proxy
```bash
pkill -f "socat TCP-LISTEN:18000"
nohup socat TCP-LISTEN:18000,reuseaddr,fork TCP:127.0.0.1:18010 >/tmp/socat-18000.log 2>&1 &
```

### Qwen-Agent / Nova Services
- Restart any FastAPI or CLI wrappers after vLLM restarts to avoid stale connections.
- Clear `/data/nova/tmp` if file ownership issues arise.

---

## 4. Escalation & Logging

1. Record incident in `project/ops_history.md` with timestamp, symptom, actions taken, and resolution.
2. If a regression originates from Forge or infrastructure changes (GPU driver, kernel upgrades), alert the PlatformOps contact and share logs (`/data/dev-vllm/reports/logs`, `/tmp/socat-*.log`).
3. For model-level anomalies (hallucinations, persistent garbling), capture sample request/response pairs and raise with ModelOps; include the vLLM commit/version.

---

## 5. Hardening Reminders

- Patch vLLM promptly; monitor advisories such as the GitLab Qwen parser disclosure.
- Limit exposure: even though port 18000 is proxied, keep firewalls restricting access to approved subnets.
- Log tool invocations (stdout/stderr) for auditability; rotate `/data/nova/logs` via logrotate.
- Re-run the **coder_endpoint_validation** runbook after any change to confirm the system returns to a known-good state.
