# Coder Endpoint Configuration Reference

Centralize environment variables, systemd units, and command snippets required to operate the coder lane. Use this document to confirm values before executing runbooks.

## 1. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NOVA_LLM_SERVER` | `http://10.0.1.1:18000/v1` | Primary endpoint for Nova, sanity scripts, and assistant wrappers |
| `NOVA_LLM_MODEL` | `Qwen/Qwen3-VL-30B-A3B-Thinking-FP8` | Generalist fallback (optional) |
| `NOVA_CODER_LLM_SERVER` | `http://127.0.0.1:8000/v1` | Direct access to coder vLLM (new sanity script default) |
| `NOVA_CODER_LLM_MODEL` | `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` | Target coder model |
| `NOVA_CODER_LLM_API_KEY` | `local-test` | API key supplied to vLLM OpenAI server |
| `NOVA_CODER_LLM_GENERATE_CFG` | `{"use_raw_api":true,"function_choice":"auto","parallel_function_calls":true,"temperature":0}` | Qwen-Agent generate config for coder lane |
| `QWEN_AGENT_DEFAULT_WORKSPACE` | `/data/nova` | Workspace for transcripts, artifacts, and code interpreter |
| `NOVA_SANITY_WORKDIR` | `./nova_sanity_workspace` | Workspace used by the sanity runner |

Set persistent values in `/etc/profile.d/nova_coder.sh` or the service unit environment files.

## 2. Key Commands

### 2.1 vLLM Launch
```bash
VLLM_USE_DEEP_GEMM=1 CUDA_LAUNCH_BLOCKING=1 \
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  --trust-remote-code \
  --dtype float16 \
  --tensor-parallel-size 1 \
  --max-model-len 262144 \
  --gpu-memory-utilization 0.95 \
  --host 0.0.0.0 \
  --port 18010 \
  --api-key local-test \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

### 2.2 Proxy Forwarders
```bash
nohup socat TCP-LISTEN:18000,reuseaddr,fork TCP:127.0.0.1:18010 >/tmp/socat-18000.log 2>&1 &
# optional
nohup socat TCP-LISTEN:8000,reuseaddr,fork TCP:127.0.0.1:18000 >/tmp/socat-8000.log 2>&1 &
```

### 2.3 Sanity Runner
```bash
cd /data/Qwen-Agent
PYTHONPATH=. python scripts/nova_tool_sanity.py
```
Use `--phase direct` or `--phase llm` to run partial phases if needed.

## 3. Systemd Templates

### 3.1 vLLM Service (`/etc/systemd/system/vllm-coder.service`)
```ini
[Unit]
Description=Qwen3-Coder vLLM Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ops
Environment=VLLM_USE_DEEP_GEMM=1
Environment=CUDA_LAUNCH_BLOCKING=1
WorkingDirectory=/srv/vllm
ExecStart=/srv/vllm/venv/bin/python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
    --trust-remote-code \
    --dtype float16 \
    --tensor-parallel-size 1 \
    --max-model-len 262144 \
    --gpu-memory-utilization 0.95 \
    --host 0.0.0.0 \
    --port 18010 \
    --api-key local-test \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_coder \
    --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Restart=always
RestartSec=10
StandardOutput=append:/var/log/vllm-coder.log
StandardError=append:/var/log/vllm-coder.err

[Install]
WantedBy=multi-user.target
```

### 3.2 socat Proxy (`/etc/systemd/system/socat-coder.service`)
```ini
[Unit]
Description=Forward 18000 to coder vLLM
After=vllm-coder.service

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:18000,reuseaddr,fork TCP:127.0.0.1:18010
Restart=always
RestartSec=2
StandardOutput=append:/var/log/socat-18000.log
StandardError=append:/var/log/socat-18000.err

[Install]
WantedBy=multi-user.target
```

Enable both services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vllm-coder.service socat-coder.service
```

## 4. Log Locations

| Path | Description |
|------|-------------|
| `/var/log/vllm-coder.log` | vLLM stdout (if using systemd unit) |
| `/var/log/socat-18000.log` | Proxy logs |
| `/tmp/socat-*.log` | Logs when run manually |
| `/data/dev-vllm/reports/logs/vllm_coder_server.log` | Default vLLM log path when launched manually |
| `/data/nova/logs/` | Sanity runner output (if redirected) |

## 5. Secrets

Store API keys and credentials in `/data/secrets` (owned by the ops user, `chmod 600`):
- `HUGGING_FACE_HUB_TOKEN` (env or `hf_token.env`)
- Serper/Tavily keys for web tools, as needed.
- Database profiles (if enabling `sql_tool`).

Include `EnvironmentFile=-/data/secrets/*.env` in relevant systemd units to load them at startup.

## 6. Change Management Checklist

- [ ] Update environment files and systemd units when ports or API keys change.
- [ ] Run the **coder_endpoint_validation** suite after any change.
- [ ] Update `docs/reference/coder_endpoint_architecture.md` and `project/ops_history.md` with new configuration details.

Maintain this reference as the authoritative source for configuration values used across automation and runbooks. 
