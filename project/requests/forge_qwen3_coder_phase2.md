# Forge Launch Request — Qwen3-Coder Phase 2

- **Request ID**: NOVA-P2-ROUTER-001
- **Date**: 2025-10-07
- **Owner**: Chase (NovaOps)
- **Assignee**: Forge (PlatformOps)

## Objective
Stand up the Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 specialist endpoint and validate Nova’s router bundle ahead of the Phase 2 handoff.

## Deliverables
1. vLLM endpoint serving `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` with OpenAI-compatible API.
2. Router smoke tests executed from `/data/nova/artifacts/nova_router_phase2/`.
3. Confirmation back to NovaOps (Chase) with endpoint URL and smoke-test artifacts.

## Artifacts & Config
- Bundle directory: `/data/nova/artifacts/nova_router_phase2/`
  - `nova_router.py`
  - `nova_tool_sanity.py`
  - `qwen3_coder_30b_fp8.md`
  - `nova_router_smoke.sh`
  - `README.md` (env vars + instructions)
- Required env vars (load into nova.env or service unit):
  ```bash
  export NOVA_LLM_SERVER=http://10.0.1.1:18000/v1
  export NOVA_LLM_MODEL=Qwen/Qwen3-VL-30B-A3B-Thinking-FP8
  export NOVA_CODER_LLM_SERVER=http://<coder-host>:18010/v1
  export NOVA_CODER_LLM_MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
  export NOVA_ROUTER_LLM_SERVER=${NOVA_LLM_SERVER}
  export PYTHONPATH=/data/Qwen-Agent${PYTHONPATH:+:$PYTHONPATH}
  export QWEN_AGENT_DEFAULT_WORKSPACE=/data/nova
  ```
- Launch reference: `docs/qwen3_coder_30b_fp8.md`

## Required Actions
1. Provision GPU host (H200 or equivalent) and pull Qwen3-Coder FP8 weights.
2. Launch vLLM with flags:
   ```bash
   python -m vllm.entrypoints.openai.api_server \
       --model Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
       --tensor-parallel-size 1 \
       --enable-auto-tool-choice \
       --tool-call-parser hermes \
       --reasoning-parser qwen3 \
       --host 0.0.0.0 \
       --port 18010
   ```
3. Export env vars (above) on the Nova control host; ensure `nova_control_server` picks them up.
4. Run smoke bundle:
   ```bash
   cd /data/nova/artifacts/nova_router_phase2
   ./nova_router_smoke.sh
   ```
5. Capture outputs:
   - `nova_tool_sanity` log snippet
   - Router responses (generalist + coder)
   - `model_switch` entry from `/data/nova/logs/transcript-*.jsonl`
6. Report back to Chase with endpoint URL, timestamp, and any follow-up issues.

## Dependencies / Risks
- GPU capacity must be allocated for the 30B FP8 model (approx. 38 GB VRAM).
- Hermes parser must remain enabled; otherwise router calls will fail.
- Ensure `/data/nova/logs` writable for transcript events.

## Completion Criteria
- vLLM endpoint reachable and authenticated if applicable.
- `nova_router_smoke.sh` completes without error.
- Transcripts show `model_switch` events for both generalist and coder paths.
- Confirmation sent to NovaOps with artifacts attached or linked.

## Contact
- Chase (NovaOps): chase@novaops.internal
- Atlas (NovaOps): atlas@novaops.internal

