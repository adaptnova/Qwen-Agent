#!/usr/bin/env python3
"""Run a quick end-to-end sanity check of Nova's core tools."""

import json
import os
import textwrap

from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message


def build_agent() -> Assistant:
    llm_cfg = {
        'model': os.getenv('NOVA_LLM_MODEL', 'Qwen/Qwen3-VL-30B-A3B-Thinking-FP8'),
        'model_type': 'oai',
        'model_server': os.getenv('NOVA_LLM_SERVER', 'http://10.0.1.1:18000/v1'),
        'generate_cfg': {
            'parallel_function_calls': False,
            'function_choice': 'none',
            'use_raw_api': True,
        }
    }

    tools = [
        'system_shell',
        'fs_admin',
        'http_client',
        'proc_manager',
        'search_tool',
        'web_researcher',
        'sql_tool',
        'python_executor',
        'code_interpreter',
        'retrieval',
    ]

    workspace = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova')
    os.makedirs(workspace, exist_ok=True)
    os.makedirs(os.path.join(workspace, 'tmp'), exist_ok=True)

    return Assistant(function_list=tools, llm=llm_cfg, system_message='Nova tool sanity runner', name='NovaSanity')


def run():
    agent = build_agent()
    workspace = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova')
    tmp_dir = os.path.join(workspace, 'tmp')

    results = {}

    results['system_shell'] = agent._call_tool('system_shell', json.dumps({'cmd': 'echo nova-ops-check'}))

    test_file = os.path.join(tmp_dir, 'sanity.txt')
    results['fs_admin_write'] = agent._call_tool('fs_admin', json.dumps({'op': 'write', 'path': test_file, 'content': 'NovaOps Sanity\n'}))
    results['fs_admin_read'] = agent._call_tool('fs_admin', json.dumps({'op': 'read', 'path': test_file}))

    results['http_client'] = agent._call_tool('http_client', json.dumps({'method': 'GET', 'url': 'https://example.com'}))[:400]

    results['proc_manager_ps'] = agent._call_tool('proc_manager', json.dumps({'action': 'ps'}))[:400]

    results['search_tool'] = agent._call_tool('search_tool', json.dumps({'provider': 'serper', 'query': 'NovaOps launch update', 'num_results': 2}))

    results['web_researcher'] = agent._call_tool('web_researcher', json.dumps({'query': 'NovaOps operations overview', 'num_results': 1, 'max_chars': 1500}))[:600]

    results['python_executor'] = agent._call_tool('python_executor', json.dumps({'code': 'import math\nprint("executor ok")\nresult = sum(range(1, 6))\nprint(result)\n'}))

    results['code_interpreter'] = agent._call_tool('code_interpreter', json.dumps({'code': 'print("ci ok")'}), messages=[Message(role='user', content='sanity')])[:400]

    sample_doc = os.path.join(tmp_dir, 'sanity_doc.txt')
    with open(sample_doc, 'w', encoding='utf-8') as f:
        f.write('NovaOps is the operations backbone for Nova agents. This test ensures retrieval works.')
    results['retrieval'] = agent._call_tool('retrieval', json.dumps({'query': 'What is NovaOps?', 'files': [sample_doc]}))[:400]

    try:
        results['sql_tool'] = agent._call_tool('sql_tool', json.dumps({'provider': 'postgres', 'profile': 'POSTGRES_MAIN', 'op': 'query', 'payload': {'sql': 'SELECT 1'}}))
    except Exception as exc:
        results['sql_tool'] = f'SKIPPED: {exc}'

    print('\nNova tool sanity results:\n')
    for name, value in results.items():
        print('=' * 60)
        print(name.upper())
        if isinstance(value, str):
            print(textwrap.shorten(value.strip(), width=600, placeholder='...'))
        else:
            print(value)
    print('\nDone.')


if __name__ == '__main__':
    run()
