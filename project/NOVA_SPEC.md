Nova Agent (Project “Nova”) — Technical Spec

1) Configuration
- OS: Ubuntu 24.04; root privileges.
- Workspace: /data/nova
  - export QWEN_AGENT_DEFAULT_WORKSPACE=/data/nova
- Secrets: /data/secrets (files). Example profiles:
  - /data/secrets/POSTGRES_MAIN.env
    - PGHOST=...
    - PGPORT=5432
    - PGUSER=...
    - PGPASSWORD=...
    - PGDATABASE=...
  - /data/secrets/SERPER.env
    - SERPER_API_KEY=...
    - SERPER_URL=https://google.serper.dev/search
  - /data/secrets/TAVILY.env
    - TAVILY_API_KEY=...
- vLLM endpoint: OpenAI-compatible HTTP URL; model: Qwen/Qwen3‑VL‑30B‑A3B‑Thinking‑FP8.

2) Agent Config (Qwen-Agent)
- Model: configured to vLLM endpoint; reasoning_content passthrough on.
- FnCall: Nous prompt; parallel_function_calls=True; function_choice='auto'.
- No step budgets; high MAX_LLM_CALL_PER_RUN; only per-call timeouts as needed.

3) Tools (OpenAI-compatible JSON Schemas)

3.1 system_shell
- description: Run any shell command with root privileges.
- parameters:
  {
    "type": "object",
    "properties": {
      "cmd": {"type": "string", "description": "The shell command to execute."},
      "cwd": {"type": "string", "description": "Working directory (absolute or relative)."},
      "env": {"type": "object", "description": "Environment vars to inject (name->value)."},
      "timeout": {"type": "number", "description": "Seconds before the call is aborted (0=none)."},
      "background": {"type": "boolean", "description": "Run in background and return PID."}
    },
    "required": ["cmd"]
  }
- returns: JSON {exit_code, pid?, started_at, finished_at, stdout, stderr}

3.2 python_executor (unsandboxed)
- description: Execute arbitrary Python code and capture stdout/stderr.
- parameters:
  {
    "type": "object",
    "properties": {
      "code": {"type": "string", "description": "Python code to execute."},
      "timeout": {"type": "number", "description": "Seconds before timeout (0=none)."}
    },
    "required": ["code"]
  }
- returns: [stdout, status]

3.3 code_interpreter (stateful kernel)
- description: Execute Python in a persistent Jupyter kernel; supports plotting and long iterative work.
- parameters: { "type":"object", "properties": {"code": {"type":"string"} }, "required":["code"] }

3.4 fs_admin
- description: Full filesystem operations (unrestricted).
- parameters:
  {
    "type": "object",
    "properties": {
      "op": {"type": "string", "enum":["read","write","append","list","move","copy","mkdir","rmdir","chmod","chown","stat"]},
      "path": {"type": "string"},
      "path2": {"type": "string", "description":"Destination path for move/copy."},
      "content": {"type": "string", "description":"Content for write/append."},
      "mode": {"type": "string", "description":"Octal mode for chmod (e.g., 0755)."},
      "owner": {"type": "string"},
      "group": {"type": "string"}
    },
    "required": ["op","path"]
  }

3.5 http_client
- description: HTTP(S) client for REST and downloads.
- parameters:
  {
    "type":"object",
    "properties":{
      "method":{"type":"string","enum":["GET","POST","PUT","DELETE","PATCH","HEAD"]},
      "url":{"type":"string"},
      "headers":{"type":"object"},
      "params":{"type":"object"},
      "json":{"type":"object"},
      "data":{"type":"string"},
      "timeout":{"type":"number"},
      "save_to":{"type":"string","description":"If set, stream body to this file path."},
      "verify_ssl":{"type":"boolean","default":true}
    },
    "required":["method","url"]
  }
- returns: {status, headers, body|file_path}

3.6 proc_manager
- description: Process inspection and control.
- parameters:
  {
    "type":"object",
    "properties":{
      "action":{"type":"string","enum":["ps","kill","terminate","renice","list_ports","tail"]},
      "pid":{"type":"number"},
      "signal":{"type":"string"},
      "nice":{"type":"number"},
      "path":{"type":"string","description":"File path for tail."},
      "lines":{"type":"number","description":"Lines for tail."}
    },
    "required":["action"]
  }

3.7 search_tool
- description: Web search via configurable provider (Serper or Tavily).
- parameters:
  {
    "type":"object",
    "properties":{
      "provider":{"type":"string","enum":["serper","tavily"],"description":"Default can be auto-chosen."},
      "query":{"type":"string"},
      "num_results":{"type":"number","default":10}
    },
    "required":["query"]
  }
- resolves keys from /data/secrets/SERPER.env or /data/secrets/TAVILY.env at call time.

3.8 sql_tool
- description: Interact with databases; supports Postgres, ClickHouse, Neo4j, Weaviate, Meilisearch, Elasticsearch (mode selected via provider).
- parameters:
  {
    "type":"object",
    "properties":{
      "provider":{"type":"string","enum":["postgres","clickhouse","neo4j","weaviate","meilisearch","elasticsearch"]},
      "profile":{"type":"string","description":"Connection profile name mapping to a secrets file in /data/secrets"},
      "op":{"type":"string","description":"Operation, e.g., query/insert/upsert/search/admin"},
      "payload":{"type":"object","description":"Operation arguments; e.g., SQL/Cypher/JSON body."},
      "timeout":{"type":"number"}
    },
    "required":["provider","op","payload"]
  }
- providers resolve credentials from matching env files under /data/secrets (e.g., POSTGRES_MAIN.env, CLICKHOUSE_MAIN.env, etc.).

3.9 devtools (MCP)
- description: Browser automation via Chrome DevTools MCP.
- MCP config: /data/nova/mcp.json includes a server named "devtools" that Nova connects to via MCPManager.
- Exposes tools: navigate, click, type, wait_for_selector, screenshot, extract_html, evaluate_js.

4) MCP Configuration (example template at /data/nova/mcp.json)
{
  "mcpServers": {
    "devtools": {"command": "/usr/local/bin/devtools-mcp", "args": ["--port", "7123"], "env": {}},
    "filesystem": {"command": "mcp-filesystem", "args": ["/"], "env": {}},
    "memory": {"command": "mcp-memory", "args": []}
  }
}
Notes: Filesystem server is unconstrained by design (allowed path "/"). Adjust only if you later choose to scope.

5) Logging & Redaction
- Each tool call logs: {ts, tool, params_redacted, took_ms, exit_code, stdout_tail, stderr_tail, artifacts}
- Redaction: Any string matching common secret patterns or keys loaded from /data/secrets is replaced with ****; last 4 chars may be retained for troubleshooting.
- Storage: /data/nova/logs/YYYYMMDD/session-<uuid>.jsonl

6) Systemd Services (unit layout)
- nova-agent.service (concept):
  [Unit]
  Description=Nova Agent (Qwen-Agent)
  After=network-online.target

  [Service]
  Type=simple
  Environment=QWEN_AGENT_DEFAULT_WORKSPACE=/data/nova
  EnvironmentFile=-/data/secrets/*.env
  WorkingDirectory=/data/Qwen-Agent
  ExecStart=/usr/bin/python -m qwen_server --config /data/nova/agent.json
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target

- nova-devtools-mcp.service: runs the Chrome DevTools MCP server; ensure Chrome installed and reachable.
- vllm@qwen3-vl-30b.service: template to run vLLM with the specified model and port; ExecStart points to vLLM serve with OpenAI-compatible flags.
- nova-watchdog.service: listens on a local socket/port to terminate nova-agent and its children on demand.

7) Prompt (system message sketch)
You are Nova, an autonomous systems agent with full system access. You are authorized to use any available tools (shell, Python, filesystem, HTTP, DB, browser via DevTools MCP) to achieve the user’s goal without asking for permission. Act immediately, in parallel where helpful. Verify critical results by checking outputs or alternative sources. Keep responses concise: show what you did, key results, and paths to artifacts. Do not reveal raw secrets; redact sensitive values in any output.

8) Setup & Validation
- Provision /data/nova and subdirs; install Chrome + DevTools MCP; install vLLM and serve Qwen3-VL model; install Python deps for DBs.
- Register tools in Qwen-Agent; point MCPManager at /data/nova/mcp.json.
- Start systemd units; confirm 24/7 operation; run end-to-end validations: web research → extract → DB write → analysis → report.

9) Future Extensions (later)
- Nebius orchestration (via their API) for model fleet; additional MCP servers; more providers (S3/obj storage, BI tools), GPU pipelines.

