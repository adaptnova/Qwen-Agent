#!/usr/bin/env python3
"""
nova_tool_e2e_shim.py  (v1.2)
Direct OpenAI-compatible tool-calling loop against your vLLM endpoint, with local tool execution.
Adds forced finalization after tool runs (tool_choice='none') and safe fallback to tool stdout.

Env (defaults shown):
  NOVA_CODER_LLM_SERVER=http://127.0.0.1:8000/v1
  NOVA_CODER_LLM_MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
  NOVA_CODER_LLM_API_KEY=local-test
"""
import os, sys, json, subprocess, base64, time, traceback
from typing import Dict, Any, List, Tuple
import urllib.request

SERVER = os.getenv("NOVA_CODER_LLM_SERVER", "http://127.0.0.1:8000/v1")
MODEL  = os.getenv("NOVA_CODER_LLM_MODEL", "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8")
APIKEY = os.getenv("NOVA_CODER_LLM_API_KEY", "local-test")

def http_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(f"{SERVER}{path}", method="POST")
    req.add_header("Authorization", f"Bearer {APIKEY}")
    req.add_header("Content-Type", "application/json")
    data = json.dumps(payload).encode("utf-8")
    with urllib.request.urlopen(req, data=data, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))

# ------------ Local tools (argv only, no shell) ------------
def tool_system_shell(arguments: Dict[str, Any]) -> Dict[str, Any]:
    cmd = arguments.get("cmd")
    timeout = int(arguments.get("timeout", 20))
    if not isinstance(cmd, list) or not all(isinstance(x, str) for x in cmd):
        return {"error":"cmd must be list[str]"}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired as te:
        return {"error":"timeout", "stdout": te.stdout, "stderr": te.stderr}
    except Exception as e:
        return {"error": str(e)}

def tool_read_file(arguments: Dict[str, Any]) -> Dict[str, Any]:
    path = arguments.get("path")
    max_bytes = int(arguments.get("max_bytes", 1024*1024))
    try:
        with open(path, "rb") as f:
            b = f.read(max_bytes + 1)
        if not b:
            return {"path": path, "size":0, "content": ""}
        try:
            return {"path": path, "size": len(b), "content": b.decode("utf-8")}
        except UnicodeDecodeError:
            return {"path": path, "size": len(b), "base64": base64.b64encode(b[:max_bytes]).decode("ascii")}
    except Exception as e:
        return {"error": str(e)}

def tool_write_file(arguments: Dict[str, Any]) -> Dict[str, Any]:
    path = arguments.get("path")
    content = arguments.get("content","")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"written": True, "path": path, "bytes": len(content.encode("utf-8"))}
    except Exception as e:
        return {"error": str(e)}

def tool_http_get(arguments: Dict[str, Any]) -> Dict[str, Any]:
    url = arguments.get("url")
    headers = arguments.get("headers") or {}
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            text = body.decode("utf-8", errors="ignore")
            return {"status": resp.status, "headers": dict(resp.headers), "text": text[:100_000]}
    except Exception as e:
        return {"error": str(e)}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "system_shell",
            "description": "Execute a command (argv list only) on the server and return stdout/stderr/exit_code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer"},
                },
                "required": ["cmd"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file. Returns content as UTF-8 or base64 if binary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_bytes": {"type": "integer"}
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text to a file (overwrite).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path","content"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "http_get",
            "description": "HTTP GET a URL and return status, headers, and first 100k chars of body.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "headers": {"type": "object"}
                },
                "required": ["url"],
                "additionalProperties": False
            }
        }
    }
]

HANDLERS = {
    "system_shell": tool_system_shell,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "http_get": tool_http_get,
}

def chat(messages: List[Dict[str, Any]], tools=TOOLS, tool_choice="auto") -> Dict[str, Any]:
    body = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": tool_choice,
        "temperature": 0
    }
    return http_post("/chat/completions", body)

def _extract_last_tool_stdout(messages: List[Dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "tool":
            try:
                data = json.loads(m.get("content") or "{}")
            except Exception:
                data = {}
            if isinstance(data, dict) and "stdout" in data and isinstance(data["stdout"], str):
                return data["stdout"]
    return ""

def run_loop(user_prompt: str, max_steps: int = 6) -> Tuple[str, List[Dict[str, Any]]]:
    messages = [{"role":"user","content": user_prompt}]
    steps = 0
    while True:
        steps += 1
        if steps > max_steps:
            # As a last resort, return the most recent tool stdout to avoid infinite loops
            return (_extract_last_tool_stdout(messages), messages)
        resp = chat(messages, tool_choice="auto")
        if not resp.get("choices"):
            raise RuntimeError(f"empty choices: {resp}")
        msg = resp["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        if tool_calls:
            # execute each call, append tool result messages
            for call in tool_calls:
                fn = call["function"]["name"]
                args = call["function"].get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                handler = HANDLERS.get(fn)
                result = {"error": f"unknown tool: {fn}"} if not handler else handler(args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": fn,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            # Force the model to verbalize a final answer without more tools.
            resp2 = chat(messages, tool_choice="none")
            if resp2.get("choices"):
                msg2 = resp2["choices"][0]["message"]
                if msg2.get("content"):
                    return (msg2["content"], messages + [msg2])
                # If it still refuses to speak, loop again and eventually fall back to tool stdout.
            continue
        # no tool_calls; use content as final
        return (msg.get("content") or "", messages + [msg])

def main():
    try:
        print(f"Server: {SERVER}  Model: {MODEL}")
        out1, _ = run_loop("Use system_shell to run the argv list ['echo','NOVA_E2E']; return only the stdout.")
        print("[e2e_system_shell]", "PASS" if "NOVA_E2E" in out1 else "FAIL", out1[:200])
        out2, hist2 = run_loop("Use system_shell to run the argv list ['python3','-c','print(6*7)']; return only the printed number.")
        # Accept either a final assistant message or the last tool's stdout
        final_or_stdout = out2 or _extract_last_tool_stdout(hist2)
        print("[e2e_compute_42]", "PASS" if "42" in final_or_stdout else "FAIL", (final_or_stdout or "")[:200])
        testp = os.path.abspath("./e2e_test.txt")
        out3, _ = run_loop(f"Write 'alpha-beta-gamma' to the file path '{testp}' using write_file, then read it with read_file and return only the content.")
        print("[e2e_read_write_file]", "PASS" if "alpha-beta-gamma" in out3 else "FAIL", out3[:200])
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
