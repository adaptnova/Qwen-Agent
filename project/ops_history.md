# NovaOps Operations History

This document tracks chronology of deployments, environment changes, and tooling updates.

> _Maintained by Nova (Atlas) to keep Forge/Chase aligned on recent work._

## 2025-10-06

### 19:30–22:05 UTC — Internal launch prep
- Installed full Qwen-Agent tool suite with extras (RAG, MCP, code interpreter, python executor).
- Added `scripts/nova_tool_sanity.py` to verify system_shell, fs_admin, http_client, search_tool, web_researcher, python_executor, code_interpreter, retrieval.
- Configured `/data/secrets/nova.env` with vLLM endpoint (internal), Serper/Tavily keys.
- Documented multi-phase roadmap (model fleet expansion, domain toolkits, observability, automation).
- Created interactive CLI (`scripts/nova_cli.py`, alias `nn`) for Chase/Nova to co-create using the tool stack; responses logged under `/data/nova/logs/` with timing info.
- Widened repo PATH defaults so `nn` is usable across sessions.

### 21:45–22:00 UTC — Tool execution enablement
- Forge enabled vLLM flags `--enable-auto-tool-choice --tool-call-parser hermes` + bumped Nova default generate config (temperature, max tokens, top_p).
- Patched Qwen-Agent to accept parser chunks where tool arguments stream as `None` and to respect `NOVA_LLM_GENERATE_CFG`.
- Confirmed real tool execution works (`system_shell` returning `/data/Qwen-Agent`) with 17 s end-to-end latency due to thinking model.


### 2025-10-07T00:20:06+0000 — CLI prompt + model docs
- Updated Nova CLI prompt so the agent proactively executes tools (even for capability queries).
- Noted follow-up to widen tool-trigger conditions per Chase’s request.
- Documented Qwen3-Coder-30B-A3B-Instruct-FP8 deployment details in `docs/qwen3_coder_30b_fp8.md` (context size, sampling, vLLM flags, tool-calling notes).

### 2025-10-07T03:05:00+0000 — Coder router bundle handoff
- Realigned defaults to internal Nova vLLM endpoint and Qwen3-Coder FP8 specialist across router/scripts.
- Packaged `/data/nova/artifacts/nova_router_phase2/` with README, smoke script, and model reference.
- Filed Forge launch request (`project/requests/forge_qwen3_coder_phase2.md`) and notified PlatformOps to begin provisioning.

### 2025-10-07T03:40:00+0000 — Thinking fleet prep
- Submitted Ray Serve request for reasoning specialist hosting (`project/requests/forge_reasoner_rayserve.md`).
- Added benchmarking harness `scripts/nova_reasoner_benchmark.py` to log comparative latency/quality data.
- Updated roadmap Milestone 2.2 to include Ray Serve deployment and benchmarking workflow.

### 2025-10-07T03:55:00+0000 — MLflow instrumentation
- Enabled optional MLflow logging in `scripts/nova_reasoner_benchmark.py` for per-run metrics and artifact capture.
- Decided to manage thinking-model experiment history through MLflow from day one.
