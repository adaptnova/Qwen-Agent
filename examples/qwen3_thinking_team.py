# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A cooperative agent team powered by a local Qwen3 thinking model."""

from __future__ import annotations

import copy
import os
from typing import Iterable, List

from qwen_agent.agents import Assistant, GroupChat
from qwen_agent.gui import WebUI


def _qwen3_thinking_llm_cfg() -> dict:
    """Return the LLM configuration for the locally hosted Qwen3 thinking model."""
    model_name = os.getenv('QWEN3_THINKING_MODEL', 'Qwen/Qwen3-32B-Instruct')
    model_server = os.getenv('QWEN3_THINKING_SERVER', 'http://localhost:8000/v1')
    api_key = os.getenv('QWEN3_THINKING_API_KEY', 'EMPTY')

    llm_cfg = {
        'model': model_name,
        'model_server': model_server,
        'api_key': api_key,
        'generate_cfg': {
            # Qwen3 exposes the deliberate reasoning trace inside the content field when
            # ``thought_in_content`` is set to True. This makes it easy to display the
            # chain-of-thought alongside the final reply.
            'thought_in_content': True,
            'extra_body': {
                # vLLM/SGLang based deployments expect the ``enable_thinking`` flag under
                # ``chat_template_kwargs``.
                'chat_template_kwargs': {'enable_thinking': True},
            },
        },
    }
    return llm_cfg


def _build_planner() -> Assistant:
    llm_cfg = copy.deepcopy(_qwen3_thinking_llm_cfg())
    return Assistant(
        llm=llm_cfg,
        name='Planner',
        description='Breaks down user goals, delegates tasks and keeps the team on track.',
        system_message=(
            'You are the planning expert in a collaborative team. Analyse the user goal, '
            'outline a short plan, delegate concrete actions to the Researcher and the '
            'Coder, and synthesise the final answer. Always reason explicitly before '
            'responding and make sure every delegated task has a clear owner.'
        ),
    )


def _build_researcher() -> Assistant:
    llm_cfg = copy.deepcopy(_qwen3_thinking_llm_cfg())
    return Assistant(
        llm=llm_cfg,
        name='Researcher',
        description='Finds information online and summarises relevant evidence.',
        system_message=(
            'You specialise in gathering facts. Whenever the plan requires external '
            'information, use the available web tools to search, follow the most relevant '
            'results and report concise evidence with citations. Do not speculate—if you '
            'cannot find an answer, state that clearly.'
        ),
        function_list=['web_search', 'web_extractor'],
    )


def _build_coder() -> Assistant:
    llm_cfg = copy.deepcopy(_qwen3_thinking_llm_cfg())
    return Assistant(
        llm=llm_cfg,
        name='Coder',
        description='Runs Python code, analyses data and validates results.',
        system_message=(
            'You are responsible for calculations, simulations and data processing. Use '
            'the code interpreter to execute Python snippets safely. Explain the logic of '
            'any code you run and summarise the outputs so the rest of the team can build '
            'on them.'
        ),
        function_list=['code_interpreter'],
    )


def init_agent_team() -> GroupChat:
    """Create the full Qwen3 thinking multi-agent team."""
    agents: List[Assistant] = [
        _build_planner(),
        _build_researcher(),
        _build_coder(),
    ]

    # ``GroupChat`` manages speaker turn-taking. With ``auto`` mode it uses a lightweight
    # host (backed by the same LLM configuration) to decide who should speak next.
    host_llm_cfg = copy.deepcopy(_qwen3_thinking_llm_cfg())

    return GroupChat(
        agents=agents,
        agent_selection_method='auto',
        llm=host_llm_cfg,
        name='Qwen3 Thinking Team',
        description='An orchestrated team of Qwen3-powered specialists using explicit reasoning.',
    )


def _display_messages(messages: Iterable[dict]) -> None:
    """Pretty-print multi-agent messages in the terminal."""
    for message in messages:
        speaker = message.get('name') or message.get('role', 'assistant')
        role = message.get('role')
        if role == 'assistant':
            if message.get('reasoning_content'):
                print(f'[{speaker} · thinking]\n{message["reasoning_content"]}\n')
            if message.get('content') and message.get('content') != message.get('reasoning_content'):
                print(f'[{speaker}]\n{message["content"]}\n')
            if message.get('function_call'):
                fn = message['function_call']
                print(f'[tool-call by {speaker}] {fn["name"]}\n{fn["arguments"]}\n')
        elif role == 'function':
            print(f'[tool-result · {message.get("name", "unknown")}]\n{message.get("content", "")}\n')
        else:
            print(f'[{speaker}]\n{message.get("content", "")}\n')


def chat_cli() -> None:
    """Run a simple CLI demo for the agent team."""
    bot = init_agent_team()
    print('Qwen3 Thinking Team is ready. Type "exit" to quit.\n')
    messages: List[dict] = []

    while True:
        query = input('User: ').strip()
        if not query:
            continue
        if query.lower() in {'exit', 'quit'}:
            break
        messages.append({'role': 'user', 'content': query})
        responses = bot.run_nonstream(messages=messages)
        _display_messages(responses)
        messages.extend(responses)


def chat_gui() -> None:
    """Launch the Gradio-based GUI for the team."""
    bot = init_agent_team()
    chatbot_config = {
        'prompt.suggestions': [
            'Summarise the latest research on solar panel efficiency.',
            'Write Python code to analyse a small data table about sales.',
            'Plan a weekend city tour and include verified opening hours.'
        ],
        'verbose': True,
    }
    WebUI(bot, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    chat_cli()
