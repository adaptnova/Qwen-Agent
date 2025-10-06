import json
import os
from typing import List

from qwen_agent.agents import Assistant
from qwen_agent.tools import (
    SystemShell,
    FSAdmin,
    HTTPClient,
    ProcManager,
    SearchTool,
    SQLTool,
    PythonExecutor,
    CodeInterpreter,
)
from qwen_agent.tools import MCPManager


def load_mcp_config(path: str):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def build_agent() -> Assistant:
    # Workspace and model config
    workspace = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova')
    os.makedirs(workspace, exist_ok=True)

    llm_server = os.getenv('NOVA_LLM_SERVER', 'http://127.0.0.1:8000/v1')  # stub; set your vLLM server URL
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

    # Tool registry: unrestricted set
    tools: List = [
        'system_shell',
        'fs_admin',
        'http_client',
        'proc_manager',
        'search_tool',
        'sql_tool',
        'python_executor',
        'code_interpreter',
        'web_search',  # optional; uses SERPER_API_KEY if present
        'retrieval',   # optional doc parsing & BM25 RAG
    ]

    system_prompt = (
        'You are Nova, an autonomous systems agent with full system access. '
        'Use any available tools (shell, Python, filesystem, HTTP, DB, DevTools MCP) to achieve goals without asking for permission. '
        'Act immediately, in parallel where helpful. Verify results by checking outputs or alternative sources. '
        'Keep responses concise: summarize actions, results, and artifact paths. Do not reveal raw secrets; redact sensitive values.'
    )

    agent = Assistant(
        function_list=tools,
        llm=llm_cfg,
        system_message=system_prompt,
        name='NovaAgent',
        description='Autonomous, root-capable super-agent',
    )

    # Initialize MCP servers if config present
    mcp_cfg_path = os.getenv('NOVA_MCP_CONFIG', os.path.join(workspace, 'mcp.json'))
    mcp_cfg = load_mcp_config(mcp_cfg_path)
    if mcp_cfg:
        MCPManager().initConfig(mcp_cfg)

    return agent


def demo():
    agent = build_agent()
    print('NovaAgent ready. Example tool-calls:')
    # 1) Run a shell command
    res = agent._call_tool('system_shell', {'cmd': 'uname -a'})
    print('system_shell:', res[:400])
    # 2) Web search
    res2 = agent._call_tool('search_tool', {'provider': 'serper', 'query': 'Qwen3 VL 30B release notes'})
    print('search_tool:', res2[:400])


if __name__ == '__main__':
    demo()

