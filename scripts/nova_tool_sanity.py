#!/usr/bin/env python3
"""
A focused sanity runner for the Qwen-Agent + vLLM tool-calling stack.

Phases:
  A) Direct tool execution (proves executors work on this host)
  B) End-to-end LLM tool calling (proves vLLM emits tool_calls and Qwen-Agent executes them)

Defaults target Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 via your local vLLM OAI endpoint.

Environment overrides (preferred for ops):
  NOVA_CODER_LLM_SERVER        default: http://127.0.0.1:8000/v1
  NOVA_CODER_LLM_MODEL         default: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
  NOVA_CODER_LLM_API_KEY       default: local-test
  NOVA_CODER_LLM_GENERATE_CFG  default: {"use_raw_api": true, "function_choice":"auto", "parallel_function_calls": true, "temperature": 0}

Requirements:
  pip install -U "qwen-agent[code_interpreter,mcp]"
  vLLM launched with: --enable-auto-tool-choice --tool-call-parser qwen3_coder
"""
import os, sys, json, time, base64, traceback, subprocess, typing as t
import datetime as _dt

# Optional dependency; only needed for http_get tool
try:
    import requests
except Exception:
    requests = None

# Qwen-Agent imports
try:
    from qwen_agent.agents import Assistant
    from qwen_agent.tools.base import BaseTool, register_tool
except Exception as e:
    print("ERROR: qwen-agent is not installed. Run: pip install -U 'qwen-agent[code_interpreter,mcp]'")
    sys.exit(2)

# -----------------------------
# Config
# -----------------------------
DEF_SERVER = os.getenv('NOVA_CODER_LLM_SERVER', 'http://127.0.0.1:8000/v1')
DEF_MODEL  = os.getenv('NOVA_CODER_LLM_MODEL', 'Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8')
DEF_KEY    = os.getenv('NOVA_CODER_LLM_API_KEY', 'local-test')

def _loads_or_default(env_name: str, default: dict) -> dict:
    raw = os.getenv(env_name, '')
    if not raw.strip():
        return default
    try:
        return json.loads(raw)
    except Exception:
        print(f"WARNING: {env_name} was not valid JSON; using default")
        return default

GEN_CFG_DEFAULT = {
    "use_raw_api": True,                 # let vLLM handle native tool-calls for Qwen3-Coder
    "function_choice": "auto",
    "parallel_function_calls": True,
    "temperature": 0
}
GEN_CFG = _loads_or_default('NOVA_CODER_LLM_GENERATE_CFG', GEN_CFG_DEFAULT)

# Workspace for temporary files
WORKDIR = os.getenv('NOVA_SANITY_WORKDIR', os.path.abspath('./nova_sanity_workspace'))
os.makedirs(WORKDIR, exist_ok=True)

# -----------------------------
# Custom local tools
# -----------------------------
@register_tool('system_shell')
class SystemShell(BaseTool):
    description = 'Execute a shell command on this machine and return stdout/stderr/exit_code as JSON.'
    parameters = [
        {"name": "cmd", "type": "array", "description": "Command and args as a JSON array of strings, e.g., [\\"echo\\", \\"hello\\"]", "required": True},
        {"name": "timeout", "type": "integer", "description": "Seconds before killing the process", "required": False},
        {"name": "cwd", "type": "string", "description": "Working directory path", "required": False}
    ]
    def call(self, params: str, **kwargs) -> str:
        data = json.loads(params) if isinstance(params, str) else (params or {})
        cmd = data.get("cmd")
        if not isinstance(cmd, list) or not all(isinstance(x, str) for x in cmd):
            return json.dumps({"error":"cmd must be a list of strings"})
        timeout = data.get("timeout", 20)
        cwd = data.get("cwd", None)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
            return json.dumps({
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            })
        except subprocess.TimeoutExpired as te:
            return json.dumps({"error":"timeout", "stdout":te.stdout, "stderr":te.stderr})
        except Exception as e:
            return json.dumps({"error": str(e)})

@register_tool('read_file')
class ReadFile(BaseTool):
    description = 'Read a text file and return its content (base64 if binary detected).'
    parameters = [
        {"name":"path", "type":"string", "description":"Absolute or relative file path", "required":True},
        {"name":"max_bytes", "type":"integer", "description":"Max bytes to read", "required":False}
    ]
    def call(self, params: str, **kwargs) -> str:
        data = json.loads(params) if isinstance(params, str) else (params or {})
        path = data.get("path")
        max_bytes = int(data.get("max_bytes", 1024*1024))
        try:
            with open(path, "rb") as f:
                b = f.read(max_bytes + 1)
            if not b:
                return json.dumps({"path":path, "size":0, "content":""})
            try:
                text = b.decode("utf-8")
                return json.dumps({"path":path, "size":len(b), "content":text})
            except UnicodeDecodeError:
                enc = base64.b64encode(b[:max_bytes]).decode("ascii")
                return json.dumps({"path":path, "size":len(b), "base64":enc})
        except Exception as e:
            return json.dumps({"error": str(e)})

@register_tool('write_file')
class WriteFile(BaseTool):
    description = 'Write text content to a file (overwrites).'
    parameters = [
        {"name":"path", "type":"string", "description":"File path to write", "required":True},
        {"name":"content", "type":"string", "description":"Text content to write", "required":True}
    ]
    def call(self, params: str, **kwargs) -> str:
        data = json.loads(params) if isinstance(params, str) else (params or {})
        path = data.get("path")
        content = data.get("content", "")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return json.dumps({"written": True, "path": path, "bytes": len(content.encode("utf-8"))})
        except Exception as e:
            return json.dumps({"error": str(e)})

@register_tool('http_get')
class HttpGet(BaseTool):
    description = 'HTTP GET a URL and return status, headers, and first 100k chars of text body.'
    parameters = [
        {"name":"url","type":"string","description":"URL to fetch","required":True},
        {"name":"headers","type":"object","description":"Optional headers","required":False}
    ]
    def call(self, params: str, **kwargs) -> str:
        if requests is None:
            return json.dumps({"error":"requests not installed"})
        data = json.loads(params) if isinstance(params, str) else (params or {})
        url = data.get("url")
        headers = data.get("headers") or {}
        try:
            r = requests.get(url, headers=headers, timeout=20)
            text = r.text[:100_000] if r.text else ""
            return json.dumps({"status": r.status_code, "headers": dict(r.headers), "text": text})
        except Exception as e:
            return json.dumps({"error": str(e)})

# -----------------------------
# Helpers
# -----------------------------
class Result:
    def __init__(self): self.ok=0; self.fail=0; self.skip=0; self.details=[]
    def add(self, name, status, note=""):
        if status=="PASS": self.ok+=1
        elif status=="SKIP": self.skip+=1
        else: self.fail+=1
        self.details.append((name, status, note))
    def summary(self):
        return f"PASS {self.ok} / FAIL {self.fail} / SKIP {self.skip}"

def _print_detail(res: Result):
    print("\\n=== Detailed Results ===")
    for name, st, note in res.details:
        line = f"[{st}] {name}"
        if note: line += f" :: {note}"
        print(line)
    print(f"---\\n{res.summary()}\\n")

# -----------------------------
# Phase A: Direct tool execution
# -----------------------------
def phase_direct(res: Result):
    print("Phase A: Direct tool execution")
    # 1) Shell
    try:
        out = SystemShell().call(json.dumps({"cmd":["echo","NOVA_DIRECT"], "timeout":10}))
        data = json.loads(out)
        if data.get("exit_code")==0 and "NOVA_DIRECT" in (data.get("stdout") or ""):
            res.add("system_shell", "PASS")
        else:
            res.add("system_shell", "FAIL", json.dumps(data)[:500])
    except Exception as e:
        res.add("system_shell", "FAIL", str(e))
    # 2) Write + Read file
    try:
        p = os.path.join(WORKDIR, "direct_test.txt")
        w = WriteFile().call(json.dumps({"path":p, "content":"hello from direct phase"}))
        rw = json.loads(w)
        r = ReadFile().call(json.dumps({"path":p}))
        rr = json.loads(r)
        if rr.get("content","").startswith("hello"):
            res.add("read_write_file", "PASS")
        else:
            res.add("read_write_file", "FAIL", json.dumps({"write":rw,"read":rr})[:500])
    except Exception as e:
        res.add("read_write_file", "FAIL", str(e))
    # 3) HTTP GET
    try:
        if requests is None:
            res.add("http_get", "SKIP", "requests not installed")
        else:
            h = HttpGet().call(json.dumps({"url":"https://example.com"}))
            hd = json.loads(h)
            if isinstance(hd.get("status"), int) and hd.get("text"):
                res.add("http_get", "PASS")
            else:
                res.add("http_get", "FAIL", json.dumps(hd)[:500])
    except Exception as e:
        res.add("http_get", "FAIL", str(e))

# -----------------------------
# Phase B: End-to-end via LLM tool-calling
# -----------------------------
def _build_assistant():
    llm_cfg = {
        "model": DEF_MODEL,
        "model_type": "oai",
        "model_server": DEF_SERVER,
        "api_key": DEF_KEY,
        "generate_cfg": GEN_CFG
    }
    tools = ["system_shell", "read_file", "write_file", "http_get", "code_interpreter"]
    bot = Assistant(llm=llm_cfg, function_list=tools)
    return bot

def _run_e2e_prompt(bot: Assistant, prompt: str, timeout_s: int = 60) -> str:
    msgs = [{"role":"user", "content": prompt}]
    chunks = []
    start = time.time()
    for resp in bot.run(messages=msgs):
        # resp is typically a dict message or list at the end; collect text if present
        if isinstance(resp, dict) and resp.get("content") is not None:
            chunks.append(str(resp.get("content")))
        if time.time() - start > timeout_s:
            raise TimeoutError("E2E run timed out")
    return "".join(chunks)

def phase_e2e(res: Result):
    print("Phase B: LLM-driven tool-calling via vLLM -> tool_calls -> Qwen-Agent")
    try:
        bot = _build_assistant()
    except Exception as e:
        res.add("assistant_init", "FAIL", str(e))
        return
    # 1) Shell via tool call
    try:
        text = _run_e2e_prompt(bot, "Use system_shell to run: echo NOVA_E2E; then return only the stdout string.")
        if "NOVA_E2E" in text:
            res.add("e2e_system_shell", "PASS")
        else:
            res.add("e2e_system_shell", "FAIL", text[:400])
    except Exception as e:
        res.add("e2e_system_shell", "FAIL", str(e))
    # 2) Code interpreter simple math
    try:
        text = _run_e2e_prompt(bot, "Use the code_interpreter tool to compute 6*7 and return just the number.")
        if "42" in text:
            res.add("e2e_code_interpreter", "PASS")
        else:
            res.add("e2e_code_interpreter", "FAIL", text[:400])
    except Exception as e:
        res.add("e2e_code_interpreter", "FAIL", str(e))
    # 3) Read/write via tools
    try:
        p = os.path.join(WORKDIR, "e2e_test.txt")
        text = _run_e2e_prompt(bot, f"Write 'alpha-beta-gamma' to the file path '{p}' using write_file, then read it with read_file and return the content.")
        if "alpha-beta-gamma" in text:
            res.add("e2e_read_write_file", "PASS")
        else:
            res.add("e2e_read_write_file", "FAIL", text[:400])
    except Exception as e:
        res.add("e2e_read_write_file", "FAIL", str(e))

def main():
    print(f"Config: server={DEF_SERVER} model={DEF_MODEL} raw_api={GEN_CFG.get('use_raw_api')} func_choice={GEN_CFG.get('function_choice')} parallel={GEN_CFG.get('parallel_function_calls')}")
    res = Result()
    try:
        phase_direct(res)
        phase_e2e(res)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception:
        traceback.print_exc()
        res.add("internal_error", "FAIL", "unhandled exception")
    _print_detail(res)
    print(res.summary())
    # Exit code 0 on full pass, 1 otherwise
    sys.exit(0 if (res.fail==0) else 1)

if __name__ == "__main__":
    main()
