# Coder Endpoint Architecture Overview

This document summarizes the deployed architecture for the Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 model with native tool calling. It distills the detailed narrative from `docs/Qwen Agent setup guide.md` and related conversations into an actionable reference.

## 1. Core Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| Inference | **vLLM** (`Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`) | Hosts the model with FP8 weights, serves OpenAI-compatible API, emits native `tool_calls` using the `qwen3_coder` parser |
| Proxy | **socat** (18000 → 18010) | Maintains legacy OpenAI endpoint on 18000 while the vLLM server listens on 18010 |
| Agent | **Qwen-Agent** | Manages tools, code interpreter, and optional MCP servers; executes tool calls returned by the model |
| Clients | Nova, Open WebUI, CI scripts | Consume the OpenAI interface; either send pure chat requests or rely on the agent’s tool execution |

## 2. Data Flow

```
Client (Open WebUI / Nova / script)
        │  HTTP POST /v1/chat/completions
        ▼
socat proxy (port 18000)
        │  TCP forward
        ▼
vLLM OpenAI server (port 18010)
        │  Generates tool_calls via qwen3_coder parser
        ▼
Qwen-Agent (function_list + code_interpreter)
        │  Executes tools locally (system_shell, read/write, HTTP, etc.)
        ▼
Response assembled (with tool outputs) and returned to client
```

### Notes
- The agent can expose its own HTTP interface (FastAPI/uvicorn) or be embedded in a shim that mimics OpenAI’s API. Clients should rely on the agent for tool execution rather than talking to vLLM directly if they expect tools to run.
- MCP servers may be attached locally (root access) or remotely (client-hosted) depending on the need. Execution location is determined by where the MCP server runs.

## 3. Ports & Endpoints

| Port | Endpoint | Description |
|------|----------|-------------|
| 18010 | `http://10.0.1.1:18010/v1` | Raw vLLM OpenAI server (local access only) |
| 18000 | `http://10.0.1.1:18000/v1` | Public OpenAI endpoint via socat proxy; **primary entry point** |
| 8000 (optional) | `http://10.0.1.1:8000/v1` | Secondary shim for legacy clients (proxy to 18000) |
| 7125 (optional) | Nova control server | Runs only when `nova_control_server.py` is active |

## 4. Tool & MCP Strategy

- **Built-in tools**: system shell, file read/write, HTTP GET, code interpreter. These run on the GPU host with full privileges when the agent is executed as root/ops user.
- **MCP servers**:
  - Local: filesystem, shell, fetch servers can be launched alongside the agent for unrestricted access.
  - Remote: clients can host additional MCP services if they want execution on their own machines; the agent connects to those endpoints when configured.

## 5. Security Considerations

- Running code interpreter and shell tools without sandboxing is powerful but dangerous. Ensure the agent runs under a controlled account (`sudo` as needed) and restrict network access to trusted subnets.
- Apply vLLM security patches promptly (minimum version `0.10.1.1` to avoid the Qwen parser RCE).
- Implement authentication for public endpoints (API key or reverse proxy) if exposing beyond a trusted network.

## 6. Documentation Links

- `docs/runbooks/coder_endpoint_setup.md`
- `docs/runbooks/coder_endpoint_validation.md`
- `docs/runbooks/coder_endpoint_troubleshooting.md`
- `docs/Qwen Agent setup guide.md` (source narrative)

Maintain this architecture note whenever ports, proxies, or the agent stack change. It should always reflect the live system. 
