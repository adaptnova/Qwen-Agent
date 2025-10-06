Nova Agent (Project “Nova”) — Product Requirements Document (PRD)

Vision
- Nova is a fully autonomous, real-time super-agent that operates 24/7 with unrestricted system access to execute research, browsing, data/ETL, analysis, DB operations, and model-serving tasks, reporting progress and outcomes without human intervention.

Scope
- Platform: Ubuntu 24.04 VM (spot), root privileges, persistent /data volume.
- Backend: Self-hosted vLLM (OpenAI-compatible) serving Qwen/Qwen3‑VL‑30B‑A3B‑Thinking‑FP8.
- Workspace: /data/nova; Secrets in /data/secrets.
- Tooling: Unconstrained, root-capable tools; Chrome DevTools MCP for browser automation. No Docker/K8s; manage services with systemd.

Goals
- Hands-off autonomy (HOOTL): Nova independently plans, executes, and verifies tasks across web, system, data, and ML domains with minimal prompting.
- Real-time operation: Always-on; resilient restarts; no step budgets or TTL limits beyond per-call timeouts to prevent indefinite hangs.
- Broad integration: Databases (Postgres, ClickHouse, Weaviate, Neo4j, Meilisearch, Elasticsearch), web search (Serper/Tavily), filesystems, HTTP(S), processes, and browser automation.

Non-Goals
- Human-in-the-loop browser extensions at launch.
- Container/K8s-based orchestration.
- Artificial “step budgets” or confirmation prompts.

Primary User Stories
- As an R&D operator, I point Nova at a research goal; it searches, navigates, extracts data, stores/query DBs, analyzes with Python, and produces a report.
- As a data engineer, I ask Nova to set up and run ETL pipelines that pull from HTTP/FTP/APIs, write to Postgres/ClickHouse/Elasticsearch, and validate results.
- As a platform operator, I instruct Nova to deploy/update the vLLM model services via systemd, test endpoints, and route workloads.
- As a knowledge worker, I ask Nova to browse, scrape, and summarize large multi-page sites with screenshots and citations, storing raw extracts for future use.

Functional Requirements
- Core tools: system_shell, PythonExecutor, CodeInterpreter, fs_admin, http_client, proc_manager.
- Browser automation via Chrome DevTools MCP with actions (navigate/click/type/wait), extraction (HTML/JS eval), screenshots.
- Web search with Serper and/or Tavily; provider can be selected dynamically.
- Database connectors:
  - Postgres/ClickHouse: read/write queries, schema introspection, bulk ingest.
  - Weaviate: class/schema mgmt, vector upsert, search.
  - Neo4j: Cypher queries.
  - Meilisearch: index mgmt, search.
  - Elasticsearch: index mgmt, ingest, queries.
- RAG and document parsing with SimpleDocParser/WebExtractor; integrate with DB/vector stores as needed.
- MCP servers: devtools, filesystem (unconstrained), memory; attach via /data/nova/mcp.json.

Operational Requirements
- Systemd services with Restart=always; logs to journald + /data/nova/logs.
- 24/7 availability; recover from crashes without human intervention.
- Logging and audit for all tool calls; secrets redaction in logs.
- Only per-call timeouts (configurable) to avoid hangs; no job TTLs or budgets.

Metrics / KPIs
- Task completion rate without human intervention.
- Mean time to recovery (process restarts) and durability (uptime).
- End-to-end latency for typical workflows.
- Incidence of tool call failures and automatic retries.

Dependencies
- vLLM with the specified Qwen3 model; Google Chrome + DevTools MCP server; Python deps (requests, DB drivers, etc.).
- Network egress to target services (web, DBs, search APIs).

Risks & Mitigations
- Risk: Overreach or destructive actions due to unlimited access.
  - Mitigation: Explicit system prompt guardrails (do not exfiltrate secrets, confirm destructive intent in reasoning), logging/audit, kill switch.
- Risk: Long-running jobs consuming system resources.
  - Mitigation: Per-call timeouts, proc_manager visibility, and watchdog cleanup.
- Risk: Credential exposure in logs.
  - Mitigation: Redaction middleware; secrets read from /data/secrets; no plaintext echo in transcripts.

Acceptance Criteria
- Nova runs as a systemd service, restarts automatically, and performs autonomous end-to-end tasks with no HIL.
- Browser automation works headless via DevTools MCP; Nova can navigate, interact, extract, and screenshot.
- Database connectors perform read/write and basic admin flows for the listed targets.
- Logs are written to /data/nova/logs with redacted secrets and tool call details.

