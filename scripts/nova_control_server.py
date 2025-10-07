#!/usr/bin/env python3
import os
import json
import time
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from qwen_agent.agents import Assistant
from qwen_agent.tools import (
    SystemShell, FSAdmin, HTTPClient, ProcManager, SearchTool, SQLTool, PythonExecutor, CodeInterpreter
)
from qwen_agent.tools import MCPManager


def build_agent() -> Assistant:
    workspace = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova')
    os.makedirs(workspace, exist_ok=True)
    llm_server = os.getenv('NOVA_LLM_SERVER', 'http://10.0.1.1:18000/v1')
    llm_model = os.getenv('NOVA_LLM_MODEL', 'Qwen/Qwen3-VL-30B-A3B-Thinking-FP8')
    llm_cfg = {
        'model': llm_model,
        'model_type': 'oai',
        'model_server': llm_server,
        'generate_cfg': {
            'parallel_function_calls': True,
            'function_choice': 'auto',
            'use_raw_api': True,
            'max_input_tokens': int(os.getenv('NOVA_MAX_INPUT_TOKENS', '58000')),
        },
    }
    tools = [
        'system_shell','fs_admin','http_client','proc_manager','search_tool','sql_tool','python_executor','code_interpreter','web_search','retrieval'
    ]
    system_prompt = (
        'You are Nova, an autonomous systems agent with full system access. '
        'Use any available tools (shell, Python, filesystem, HTTP, DB, DevTools MCP) to achieve goals without asking for permission. '
        'Act immediately, in parallel where helpful. Verify results. Keep responses concise and redact secrets.'
    )
    agent = Assistant(function_list=tools, llm=llm_cfg, system_message=system_prompt, name='NovaAgent')
    mcp_cfg_path = os.getenv('NOVA_MCP_CONFIG', os.path.join(workspace, 'mcp.json'))
    if os.path.exists(mcp_cfg_path):
        MCPManager().initConfig(json.load(open(mcp_cfg_path)))
    return agent


app = FastAPI(title='Nova Control')
_agent = None


class RunRequest(BaseModel):
    prompt: str
    files: List[str] | None = None


@app.on_event('startup')
def _startup():
    global _agent
    _agent = build_agent()
    # Initialize task queue
    _init_queue()


@app.post('/run')
def run_task(req: RunRequest):
    from qwen_agent.llm.schema import Message
    messages = [Message('user', req.prompt)]
    last = None
    for last in _agent.run(messages):
        pass
    if last:
        # Redact before returning
        try:
            from qwen_agent.utils.redaction import redact
            content = last[-1].content
            if isinstance(content, str):
                content = redact(content)
            return {'result': content}
        except Exception:
            return {'result': last[-1].content}
    return {'result': ''}


# --- Health & Status ---
@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/status')
def status():
    # List background jobs from system_shell runs
    runs_dir = os.path.join(os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova'), 'runs', 'system_shell')
    jobs = []
    try:
        for name in os.listdir(runs_dir):
            meta = os.path.join(runs_dir, name, 'meta.json')
            if os.path.exists(meta):
                jobs.append(meta)
    except Exception:
        pass
    return {'background_jobs_meta': jobs, 'queue_len': _queue_len()}


# --- Simple SQLite task queue ---
import sqlite3
import threading

_queue_db_path = None
_queue_thread = None


def _init_queue():
    global _queue_db_path, _queue_thread
    root = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova')
    os.makedirs(root, exist_ok=True)
    _queue_db_path = os.path.join(root, 'nova_tasks.db')
    conn = sqlite3.connect(_queue_db_path)
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT, status TEXT, created_at REAL, updated_at REAL, result TEXT)'
    )
    conn.commit()
    conn.close()
    _queue_thread = threading.Thread(target=_worker, daemon=True)
    _queue_thread.start()


class EnqueueRequest(BaseModel):
    prompt: str


@app.post('/enqueue')
def enqueue(req: EnqueueRequest):
    ts = time.time()
    conn = sqlite3.connect(_queue_db_path)
    cur = conn.cursor()
    cur.execute('INSERT INTO tasks (prompt, status, created_at, updated_at, result) VALUES (?, ?, ?, ?, ?)',
                (req.prompt, 'queued', ts, ts, ''))
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return {'task_id': task_id}


@app.get('/tasks')
def tasks():
    conn = sqlite3.connect(_queue_db_path)
    cur = conn.cursor()
    cur.execute('SELECT id, prompt, status, created_at, updated_at FROM tasks ORDER BY id DESC LIMIT 100')
    rows = cur.fetchall()
    conn.close()
    return {'tasks': rows}


def _queue_len():
    try:
        conn = sqlite3.connect(_queue_db_path)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM tasks WHERE status = "queued"')
        n = cur.fetchone()[0]
        conn.close()
        return n
    except Exception:
        return -1


def _worker():
    import time as _t
    from qwen_agent.llm.schema import Message
    global _agent
    while True:
        try:
            conn = sqlite3.connect(_queue_db_path)
            cur = conn.cursor()
            cur.execute('SELECT id, prompt FROM tasks WHERE status = "queued" ORDER BY id ASC LIMIT 1')
            row = cur.fetchone()
            if not row:
                conn.close()
                _t.sleep(2)
                continue
            task_id, prompt = row
            cur.execute('UPDATE tasks SET status = "running", updated_at = ? WHERE id = ?', (time.time(), task_id))
            conn.commit()
            conn.close()

            # Run task
            last = None
            for last in _agent.run([Message('user', prompt)]):
                pass
            result = last[-1].content if last else ''
            try:
                from qwen_agent.utils.redaction import redact
                if isinstance(result, str):
                    result = redact(result)
            except Exception:
                pass

            conn2 = sqlite3.connect(_queue_db_path)
            cur2 = conn2.cursor()
            cur2.execute('UPDATE tasks SET status = "done", updated_at = ?, result = ? WHERE id = ?',
                         (time.time(), str(result), task_id))
            conn2.commit()
            conn2.close()
        except Exception:
            _t.sleep(2)


def main():
    port = int(os.getenv('NOVA_CONTROL_PORT', '7125'))
    log_level = os.getenv('NOVA_CONTROL_LOG_LEVEL', 'error')
    uvicorn.run(app, host='0.0.0.0', port=port, log_level=log_level)


if __name__ == '__main__':
    main()
