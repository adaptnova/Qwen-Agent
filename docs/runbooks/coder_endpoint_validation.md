# Coder Endpoint Validation Runbook

Use this runbook after provisioning or modifying the coder service. It verifies both direct tool executors and the end-to-end vLLM ↔ Qwen-Agent tool-calling path.

## 1. Preconditions

- vLLM coder service is running on port **18010** with the flags:
  `--enable-auto-tool-choice --tool-call-parser qwen3_coder`
- socat (or equivalent) forwards **18000 → 18010** for existing clients.
- Qwen-Agent (with `code_interpreter` extras) is installed.
- The updated `scripts/nova_tool_sanity.py` is present.

Optional but recommended:

```bash
export NOVA_CODER_LLM_SERVER=http://127.0.0.1:18000/v1
export NOVA_CODER_LLM_MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
export NOVA_CODER_LLM_API_KEY=local-test
export NOVA_CODER_LLM_GENERATE_CFG='{"use_raw_api":true,"function_choice":"auto","parallel_function_calls":true,"temperature":0}'
```

> The script defaults to these values; set them explicitly when testing against a non-standard host or port.

## 2. Phase A – Direct Tool Executors

This phase ensures the server host can execute the tools that Qwen-Agent will leverage.

Run:

```bash
cd /data/Qwen-Agent
PYTHONPATH=. python scripts/nova_tool_sanity.py --phase direct
```

Expectations:
- `system_shell` echoes `NOVA_DIRECT`.
- `write_file` and `read_file` operate under the sanity workspace.
- `http_get` returns HTTP 200 from a known-good URL.

Any failure here indicates a local executor problem (permissions, missing package, etc.) and must be resolved before proceeding.

## 3. Phase B – End-to-End Tool Calling

This phase proves vLLM emits native tool calls and Qwen-Agent executes them.

```
cd /data/Qwen-Agent
PYTHONPATH=. python scripts/nova_tool_sanity.py --phase llm
```

The script will:
- Trigger vLLM via the OpenAI endpoint on 18000.
- Observe `tool_calls` and invoke the locally registered tools (shell, read/write file, HTTP fetch).
- Exercise `code_interpreter` to confirm the kernel launches correctly.

**Pass criteria:** exit code 0 and summaries showing all checks as `PASS` except the expected `sql_tool` refusal (unless a Postgres profile is configured).

## 4. Manual Smoke Tests

### 4.1 Curl (no tools)
```bash
curl -sS -X POST http://10.0.1.1:18000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer sk-EMPTY' \
  -d '{"model":"Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8","messages":[{"role":"user","content":"Describe the Nova deployment pipeline."}],"max_tokens":120}'
```
Expect a clean textual response.

### 4.2 Assistant-driven tool call
```bash
python - <<'PY'
import os, json
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message

assistant = Assistant(
    function_list=['system_shell','read_file','write_file'],
    llm={
        "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8",
        "model_server": "http://10.0.1.1:18000/v1",
        "api_key": "local-test",
        "model_type": "oai",
        "generate_cfg": {"use_raw_api": True, "function_choice": "auto"}
    },
    system_message="Tool smoke test agent."
)

prompt = "Use system_shell to print $PWD, then write /tmp/coder_check.txt with the text 'coder ok'."
messages = [Message(role='user', content=prompt)]

for chunk in assistant.run(messages):
    pass

print(json.dumps(chunk[-1], indent=2, ensure_ascii=False))
PY
```
Result should show tool execution (no script prerequisites required).

### 4.3 Open WebUI
- Configure Base URL `http://10.0.1.1:18000/v1`, API key `local-test`.
- Enable tools for the model; set Function Calling to **Native**.
- Prompt: “List the files in `/data/projects/DeepCode`.”
  - Expect the model to request `system_shell` and return the directory listing.

## 5. Logging and Artifacts

After successful validation:
- Capture `/tmp/socat-18000.log` and vLLM logs.
- Archive the sanity script output (`tee` to `/data/nova/logs/coder_sanity_<timestamp>.log`).
- Update ops history (`project/ops_history.md`) with timestamped summary.

## 6. Failure Handling

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Garbled output | Missing `--tool-call-parser qwen3_coder` or wrong vLLM version | Restart vLLM with correct flags; upgrade to ≥0.10.1.1 |
| No `tool_calls` | Function calling disabled; check flags | Confirm `--enable-auto-tool-choice`; verify agent `use_raw_api` |
| HTTP 404 / 500 | socat proxy down | Restart proxy or move clients to port 18010 |
| `code_interpreter` errors | Missing extras, kernel crash | Reinstall `qwen-agent[code_interpreter]`; inspect `/tmp` kernel logs |
| `sql_tool` failure | No DB running | Configure connection or ignore if unused |

Document any unresolved issues in ops history and escalate to Forge or platform engineering as needed.
