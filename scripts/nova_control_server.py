#!/usr/bin/env python3
import os
import json
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
    llm_server = os.getenv('NOVA_LLM_SERVER', 'http://89.169.109.59:8000/v1')
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


def main():
    port = int(os.getenv('NOVA_CONTROL_PORT', '7125'))
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')


if __name__ == '__main__':
    main()
