Nova Agent (Project “Nova”) — Blueprint

Summary
- Purpose: A real-time, hands-off, autonomous super-agent running 24/7 on Ubuntu 24.04 with unrestricted, root-level tools. It operates in a disposable but persistent-data VM, using a self-hosted vLLM (OpenAI-compatible) backend for Qwen/Qwen3‑VL‑30B‑A3B‑Thinking‑FP8. Minimal prompting; Nova decides and acts.
- Workspace: /data/nova (logs, runs, datasets, tmp, tools, caches). Secrets stored as files under /data/secrets; tools read them at runtime and redact in logs.
- Browser automation: Chrome DevTools MCP (headless or headed) for fully programmatic navigation, DOM actions, extraction, screenshots, and JS eval. No human-in-the-loop browser extension.
- Orchestration: systemd only (no Docker/K8s). All services run under systemd units with logging and restart policies.
- Network: No endpoint blocks; full egress allowed. IPv6 supported.

Model & Backend
- Primary model: Qwen/Qwen3‑VL‑30B‑A3B‑Thinking‑FP8 served on vLLM (OpenAI-compatible). Enable reasoning_content passthrough.
- Agent framework: Qwen-Agent (FnCallAgent/Assistant) with Nous function-calling templates; parallel, multi-step tool calls enabled. Use raw API when beneficial.
- Optional secondary models later: Qwen3‑Coder (for code-heavy tasks) or other Qwen3 variants, spun up as additional systemd services when needed.

Data, Files, and Secrets
- Default workspace env: QWEN_AGENT_DEFAULT_WORKSPACE=/data/nova
- Directory layout (created at provisioning):
  - /data/nova/logs — JSONL transcripts + tool-call logs
  - /data/nova/runs — PID registry, job metadata, artifacts
  - /data/nova/tools — tool-specific caches or state
  - /data/nova/datasets — downloads and corpora
  - /data/nova/tmp — temporary files
  - /data/nova/caches — model/tool caches
- Secrets: real, user-specific, temporary credentials as files under /data/secrets (e.g., /data/secrets/POSTGRES_MAIN.env). Tools read values at call time and redact values in logs.

Unconstrained Tooling (Root-Capable)
- system_shell: Execute arbitrary shell commands, foreground/background; stream stdout/stderr; track PIDs; no artificial TTL (timeouts only to prevent hangs).
- PythonExecutor (unsandboxed): Run arbitrary Python with timeouts; capture stdout/stderr; ideal for programmatic tasks and analysis.
- CodeInterpreter (Jupyter kernel): Stateful Python for iterative data science/plotting.
- fs_admin: Full filesystem ops (read/write/append/list/move/copy/mkdir/rmdir/chmod/chown) with absolute paths allowed.
- http_client: HTTP(S) GET/POST/PUT/DELETE with headers/body; stream big downloads to /data/nova/datasets or /data/nova/tmp.
- proc_manager: ps/top-like views, kill/terminate/renice, list open ports, tail logs.
- search_tool: Pluggable provider (Serper/Tavily). Nova can choose per task. API keys read from /data/secrets.
- sql_tool: RDBMS/graph/vector/search connectors — Postgres, ClickHouse, Weaviate, Neo4j, Meilisearch, Elasticsearch. Connection profiles resolved from /data/secrets.
- devtools (MCP): Chrome DevTools MCP provides navigate/click/type/wait/screenshot/extract_html/evaluate_js.

MCP Integration
- Use MCPManager to attach:
  - chrome-devtools server
  - filesystem (unconstrained: allow "/" where feasible)
  - memory (ephemeral)
  - Additional servers later (e.g., DB proxies) as needed
- Configuration file: /data/nova/mcp.json (loaded on agent start).

Observability & Operations
- Logging: JSONL transcript of all agent messages and tool calls with timestamps, exit codes, and redacted secrets; stored in /data/nova/logs.
- Availability: 24/7 operation; systemd Restart=always; no step budgets or TTL constraints. Only timeouts on individual calls to avoid hangs.
- Kill switch: Local watchdog service that can terminate the agent and its child processes on command; clears background jobs.

Systemd Services (Concept)
- nova-agent.service: launches the Qwen-Agent Nova process with env pointing to /data/nova and /data/secrets. Restart=always; logs to journald + /data/nova/logs.
- nova-devtools-mcp.service: starts the Chrome DevTools MCP server; exposes local socket/port.
- vllm@qwen3-vl-30b.service: vLLM for the primary model with tuned args; additional instances (template units) as needed for other models.
- nova-watchdog.service: kill switch + orphan cleanup.

Minimal Prompting Strategy (Hands-Off)
- A concise system prompt authorizing unrestricted tool use, parallel calls, and self-verification; instruct Nova to act without asking permission and produce concise reports.
- No step budget or confirmation gates; Nova proceeds autonomously and reports results.

DB/Search Targets (Initial)
- Postgres, ClickHouse, Weaviate, Neo4j, Meilisearch, Elasticsearch.
- Provider-neutral sql_tool/search_tool with profile-based credentials under /data/secrets.

High-Level Rollout Steps
1) Provision workspace (/data/nova) and install Chrome + DevTools MCP + vLLM + Python deps.
2) Enable/implement core tools (shell, python, fs, http, proc, search, sql) and register them in Qwen-Agent.
3) Wire MCP servers (devtools, filesystem, memory) via /data/nova/mcp.json.
4) Add systemd units for agent, MCP, vLLM; configure Restart=always.
5) Validate real-world tasks end-to-end (browse → scrape → store/query DB → analyze → report), 24/7 stability.
6) Iterate prompts/tool defaults to reduce prompting further.

