#!/usr/bin/env python3
"""Interactive NovaOps CLI that exercises the full tool suite."""

import json
import os
import readline  # noqa: F401 (enables history/editing)
import sys
import time
from pathlib import Path

from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message


LOG_DIR = Path(os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova')) / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f'nova_cli_{time.strftime("%Y%m%d_%H%M%S")}.log'


def build_agent() -> Assistant:
    base_generate_cfg = {
        'temperature': 0.2,
        'max_tokens': 512,
        'use_raw_api': True,
    }
    env_cfg = os.getenv('NOVA_LLM_GENERATE_CFG')
    if env_cfg:
        try:
            base_generate_cfg.update(json.loads(env_cfg))
        except json.JSONDecodeError:
            pass

    llm_cfg = {
        'model': os.getenv('NOVA_LLM_MODEL', 'Qwen/Qwen3-VL-30B-A3B-Thinking-FP8'),
        'model_type': 'oai',
        'model_server': os.getenv('NOVA_LLM_SERVER', 'http://10.0.1.1:18000/v1'),
        'generate_cfg': base_generate_cfg,
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

    agent = Assistant(function_list=tools,
                      llm=llm_cfg,
                      system_message='You are Nova, the NovaOps agent. Execute tools when needed and respond concisely.',
                      name='Nova')
    extra_cfg = base_generate_cfg.copy()
    extra_cfg.pop('use_raw_api', None)
    agent.extra_generate_cfg = extra_cfg.copy()
    if hasattr(agent, 'mem') and agent.mem is not None:
        agent.mem.extra_generate_cfg = extra_cfg.copy()
        if getattr(agent.mem, 'llm', None):
            agent.mem.llm.generate_cfg.update(extra_cfg)
    return agent


def log(line: str):
    with LOG_FILE.open('a', encoding='utf-8') as fh:
        fh.write(line + '\n')


def format_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            txt = getattr(item, 'text', '') or getattr(item, 'image', '') or getattr(item, 'file', '')
            if txt:
                parts.append(txt)
        return '\n'.join(parts)
    return str(content)


def main():
    print("NovaOps Interactive CLI (log: {})".format(LOG_FILE))
    print("Type '/quit' or '/exit' to leave. Commands prefixed with '/shell ' run locally.")

    agent = build_agent()
    conversation = []

    while True:
        try:
            user = input('Chase> ').strip()
        except (KeyboardInterrupt, EOFError):
            print('\nExiting.')
            break

        if not user:
            continue
        if user.lower() in {'/quit', '/exit'}:
            break
        if user.startswith('/shell '):
            cmd = user[len('/shell '):]
            os.system(cmd)
            continue

        conversation.append(Message(role='user', content=user))
        log(f'CHASE: {user}')

        print('Nova>')
        start = time.time()
        *_, final_batch = agent.run(conversation)
        elapsed = time.time() - start
        # final_batch is a list of Message objects
        for msg in final_batch:
            if msg.role == 'assistant':
                text = format_content(msg.content)
                if text.strip():
                    print(text)
                    log(f'NOVA: {text}')
                    conversation.append(Message(role='assistant', content=msg.content))
            elif msg.role == 'function':
                text = format_content(msg.content)
                entry = f'[tool:{msg.name}] {text}'
                print(entry)
                log(entry)
                conversation.append(Message(role='function', name=msg.name, content=msg.content))
        print(f"(response time: {elapsed:.2f}s)")
        log(f"RESPONSE_TIME: {elapsed:.2f}s")


if __name__ == '__main__':
    main()
