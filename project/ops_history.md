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


### 2025-10-07T00:20:06+0000 — CLI prompt updates
- Refined Nova CLI system prompt to push tool-taking behavior.
- (Pending) widen tool-trigger conditions as requested.
