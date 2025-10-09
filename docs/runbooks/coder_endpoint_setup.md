# Coder Endpoint Setup Runbook

Purpose: bring up the Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 service with native tool calling on a single GPU host (H200) and expose it as an OpenAI-compatible endpoint for Nova, Open WebUI, and QA automation.

## 1. Prerequisites

| Component | Requirement |
|-----------|-------------|
| Host OS | Ubuntu 22.04/24.04 with systemd |
| GPU | NVIDIA H200 (80 GB) or equivalent Hopper-class device |
| Drivers | CUDA 12.2+ with working `nvidia-smi` |
| Python | 3.10+ (`python3-venv` package installed) |
| Networking | Port 18010 (internal) and 18000 (public/proxy) accessible; optional 8000 if exposing additional shims |
| Access | Hugging Face token with `read` permission for Qwen models |

> **Security**: run the stack under a dedicated ops user, not root. Only escalate privileges where specifically required (e.g., binding privileged ports).

## 2. Install vLLM + Dependencies

```bash
sudo apt-get update && sudo apt-get install -y python3-venv build-essential

python3 -m venv /srv/vllm/venv
source /srv/vllm/venv/bin/activate

pip install --upgrade pip
pip install "vllm>=0.10.1.1" safetensors
```

Set the Hugging Face token for the session (and persist in your shell profile if desired):

```bash
export HUGGING_FACE_HUB_TOKEN=<your_token>
```

## 3. Launch the vLLM Server (port 18010)

```bash
source /srv/vllm/venv/bin/activate

VLLM_USE_DEEP_GEMM=1 \
CUDA_LAUNCH_BLOCKING=1 \
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

Leave this process running or convert it into a systemd unit (`/etc/systemd/system/vllm-coder.service`) once verified.

## 4. Preserve the Legacy 18000 Endpoint (socat proxy)

Many clients already target port 18000. Forward traffic to the new vLLM service:

```bash
sudo apt-get install -y socat
nohup socat TCP-LISTEN:18000,reuseaddr,fork TCP:127.0.0.1:18010 \
  >/tmp/socat-18000.log 2>&1 &
```

> For production, create `socat-coder.service` under systemd to keep the proxy alive after reboots.

## 5. Sanity Check the OpenAI Endpoint

```bash
curl -sS http://127.0.0.1:18000/v1/models

curl -sS -X POST http://127.0.0.1:18000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-EMPTY" \
  -d '{
        "model":"Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8",
        "messages":[{"role":"user","content":"Summarize the Nova deployment pipeline."}],
        "max_tokens":120
      }'
```

Both commands should return clean JSON. If you see corrupted text or errors, stop and inspect the vLLM logs (`/data/dev-vllm/reports/logs/vllm_coder_server.log`).

## 6. Install Qwen-Agent with tool extras

```bash
pip install -U "qwen-agent[code_interpreter,mcp]"
```

Verify the install succeeds; the sanity runner depends on these extras.

## 7. Configure Environment (default to 18000)

Add the following to `/etc/profile.d/nova_coder.sh` or your shell profile:

```bash
export NOVA_LLM_SERVER=http://10.0.1.1:18000/v1
export NOVA_LLM_MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
export QWEN_AGENT_DEFAULT_WORKSPACE=/data/nova
mkdir -p /data/nova/{logs,runs,tmp}
```

> When using the new `nova_tool_sanity.py`, you can also set `NOVA_CODER_LLM_*` variables (server, model, api key, generate config) if the defaults differ from this host.

## 8. Optional: Expose 8000 (shim) for clients that expect that port

```bash
nohup socat TCP-LISTEN:8000,reuseaddr,fork TCP:127.0.0.1:18000 \
  >/tmp/socat-8000.log 2>&1 &
```

Only do this if you have legacy clients hard-coded to 8000; otherwise, keep the surface area small.

## 9. Next Steps

1. Follow the **coder_endpoint_validation** runbook to execute the sanity suite and manual checks.
2. Review the **coder_endpoint_troubleshooting** runbook for common issues (garbled responses, missing tool calls, auth failures).
3. Once validated, codify the vLLM process and the proxy as systemd services for durability.

---

**Reference:** The setup assumes the recommendations captured in `docs/Qwen Agent setup guide.md` and the associated chat transcript—keep those synced if the upstream model or tool-call parser changes. 
