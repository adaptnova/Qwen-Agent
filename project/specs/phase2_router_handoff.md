# Phase 2.1 Router Handoff Checklist

## Purpose
Operational checklist for handing the Nova + Qwen3-Coder router bundle to PlatformOps (Forge) so the Phase 2 specialist can be mounted quickly with the correct defaults.

## Prerequisites
- vLLM endpoint for Nova (generalist) reachable at `http://10.0.1.1:18000/v1`.
- New vLLM endpoint allocated for `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` (recommended port `18010`).
- `qwen-agent[gui,rag,code_interpreter,mcp,python_executor]` installed on the target host.
- `/data/nova` workspace prepared with the usual `{logs,runs,tools,datasets,tmp,caches}` directories.

## Env Vars (to include in nova.env or service unit)
```bash
export NOVA_LLM_SERVER=http://10.0.1.1:18000/v1
export NOVA_LLM_MODEL=Qwen/Qwen3-VL-30B-A3B-Thinking-FP8
export NOVA_CODER_LLM_SERVER=http://<coder-host>:18010/v1
export NOVA_CODER_LLM_MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
export NOVA_ROUTER_LLM_SERVER=${NOVA_LLM_SERVER}
```

Optional overrides:
```bash
export NOVA_LLM_GENERATE_CFG='{"temperature":0.7,"top_p":0.8,"parallel_function_calls":true}'
export NOVA_CODER_LLM_GENERATE_CFG='{"temperature":0.4,"top_p":0.7,"parallel_function_calls":true}'
```

## Bundle Contents (`/data/nova/artifacts/nova_router_phase2/`)
- `README.md` (hand-off instructions, env vars, smoke tests)
- `examples/nova_router.py` (router entrypoint)
- `scripts/nova_tool_sanity.py` (baseline tool diagnostic)
- `docs/qwen3_coder_30b_fp8.md` (model reference)
- `nova_router_smoke.sh` (optional wrapper to run sample prompt via router)

## Smoke Tests
1. **Tool stack**  
   ```bash
   export QWEN_AGENT_DEFAULT_WORKSPACE=/data/nova
   python scripts/nova_tool_sanity.py
   ```
2. **Router → generalist**  
   ```bash
   python examples/nova_router.py "Summarize today's NovaOps launch log."
   ```
   Expectation: stays on `Nova` (generalist) path.
3. **Router → coder**  
   ```bash
   python examples/nova_router.py "Debug this Python function that fails with a KeyError."
   ```
   Expectation: `model_switch` event shows `model=coder` in transcript and response is from Nova-Coder.

## Transcript / Audit Notes
- Router call emits `model_switch` events via `qwen_agent.utils.transcript.append_event`. Ensure `/data/nova/logs/transcript-*.jsonl` is writable.
- Confirm logrotate (`ops/logrotate/nova`) is deployed so new transcripts roll cleanly.

## Communication
- Forge to confirm coder endpoint URL + auth token (if any) before bundle install.
- Chase signs off once smoke tests capture both routing branches.

