"""Multi-agent orchestration for local Qwen3 thinking models.

This example wires up a manager agent that orchestrates a cohort of
specialists (research, coding, analytics, and creative writing).  Every
agent is powered by a Qwen3-4B thinking model that is served through an
OpenAI-compatible endpoint running on ``http://localhost:8000``.

Before running the example you should:

* Deploy ``Qwen3-4B-Instruct`` (or another reasoning variant) with
  ``enable_thinking`` support through an OpenAI-compatible server on
  port 8000.  You can use vLLM, SGLang or FastChat for this.  The
  endpoint should expose the standard ``/v1/chat/completions`` route.
* Export ``QWEN_AGENT_API_KEY`` if your gateway requires one.
* (Optional) Set ``QWEN_AGENT_MODEL`` or ``QWEN_AGENT_SERVER`` to
  override the defaults used here.

Run the example in a terminal::

    python examples/qwen3_thinking_team.py

Or launch the Gradio based WebUI::

    python examples/qwen3_thinking_team.py --gui

"""
from __future__ import annotations

import argparse
import os
from typing import Dict, Iterable, List, Optional

from qwen_agent.agents import Assistant, ReActChat, Router
from qwen_agent.gui import WebUI


DEFAULT_MODEL = os.getenv('QWEN_AGENT_MODEL', 'qwen3-4b-instruct')
DEFAULT_SERVER = os.getenv('QWEN_AGENT_SERVER', 'http://127.0.0.1:8000/v1')
DEFAULT_API_KEY = os.getenv('QWEN_AGENT_API_KEY', 'EMPTY')
DEFAULT_ENABLE_THINKING = os.getenv('QWEN_AGENT_ENABLE_THINKING', 'true').lower() not in ('0', 'false', 'no')


def _make_llm_cfg(*, enable_thinking: bool = DEFAULT_ENABLE_THINKING) -> Dict:
    """Return a fresh llm config for a single agent."""
    cfg = {
        'model': DEFAULT_MODEL,
        'model_server': DEFAULT_SERVER,
        'api_key': DEFAULT_API_KEY,
        'generate_cfg': {
            # ``extra_body`` arguments are forwarded to OpenAI-compatible APIs
            # such as vLLM/SGLang.  ``chat_template_kwargs`` works with Qwen's
            # chat template to request the thinking traces.
            'extra_body': {'enable_thinking': enable_thinking},
            'chat_template_kwargs': {'enable_thinking': enable_thinking},
            # When a response contains ``<think>`` tags the parser can split
            # the reasoning and final answer safely.
            'thought_in_content': True,
        },
    }
    return cfg


def _specialist(
    *,
    name: str,
    description: str,
    tools: Iterable,
    enable_thinking: bool = DEFAULT_ENABLE_THINKING,
) -> ReActChat:
    """Create a tool-using specialist that runs on its own model instance."""
    llm_cfg = _make_llm_cfg(enable_thinking=enable_thinking)
    return ReActChat(
        llm=llm_cfg,
        name=name,
        description=description,
        function_list=list(tools),
    )


def init_agent_service(enable_thinking: bool = DEFAULT_ENABLE_THINKING) -> Router:
    """Build the orchestrated multi-agent team."""

    research_agent = _specialist(
        name='Research Strategist',
        description=(
            'Expert researcher that can explore online resources, extract '
            'structured information from documents, and summarise findings.'
        ),
        tools=[
            'web_extractor',
            'doc_parser',
            {
                'mcpServers': {
                    'time': {
                        'command': 'uvx',
                        'args': ['mcp-server-time'],
                    }
                }
            },
        ],
        enable_thinking=enable_thinking,
    )

    coding_agent = _specialist(
        name='Code Specialist',
        description=(
            'Seasoned software engineer that designs algorithms, writes '
            'code and validates it in a sandboxed python environment.'
        ),
        tools=['code_interpreter', 'python_executor'],
        enable_thinking=enable_thinking,
    )

    analyst_agent = _specialist(
        name='Data Analyst',
        description=(
            'Data expert that inspects tables, runs computations, and builds '
            'charts to illustrate insights.'
        ),
        tools=['code_interpreter'],
        enable_thinking=enable_thinking,
    )

    creative_agent = Assistant(
        llm=_make_llm_cfg(enable_thinking=enable_thinking),
        name='Creative Writer',
        description=(
            'Skilled storyteller responsible for polishing the final '
            'deliverables and presenting consolidated conclusions.'
        ),
        function_list=['image_gen'],
    )

    orchestrator_cfg = _make_llm_cfg(enable_thinking=enable_thinking)
    orchestrator = Router(
        llm=orchestrator_cfg,
        agents=[research_agent, coding_agent, analyst_agent, creative_agent],
        name='Chief Orchestrator',
        description=(
            'Coordinates a squad of experts who each run on their own '
            'Qwen3-4B thinking model.  Delegates tasks, reviews progress, '
            'and delivers an end-to-end solution.'
        ),
    )

    return orchestrator


def run_cli_chat(query: Optional[str] = None, *, enable_thinking: bool = DEFAULT_ENABLE_THINKING) -> None:
    """Interact with the team in the terminal."""
    orchestrator = init_agent_service(enable_thinking=enable_thinking)
    messages: List[Dict] = []
    if query:
        messages.append({'role': 'user', 'content': query})

    while True:
        if not messages:
            query = input('User: ')
            if not query:
                continue
            messages.append({'role': 'user', 'content': query})

        for response in orchestrator.run(messages=messages):
            for message in response:
                content = message['content']
                if isinstance(content, list):
                    content = str(content)
                print(f"{message['role']}: {content}")
        messages.extend(response)
        next_query = input('User: ')
        if not next_query:
            continue
        if next_query.lower() in {'exit', 'quit'}:
            break
        messages.append({'role': 'user', 'content': next_query})


def launch_gui(*, enable_thinking: bool = DEFAULT_ENABLE_THINKING) -> None:
    orchestrator = init_agent_service(enable_thinking=enable_thinking)
    chatbot_config = {
        'prompt.suggestions': [
            'Create a market analysis about electric vehicles in 2025.',
            'Debug this snippet and explain the fix:\n```python\nfor i in range(10):\n    print(i**2)\n```',
            'Plan a 3-day trip to Tokyo with a daily schedule and packing list.',
        ],
        'verbose': True,
    }
    WebUI(orchestrator, chatbot_config=chatbot_config).run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Qwen3 thinking team demo.')
    parser.add_argument('--gui', action='store_true', help='Launch the Gradio based WebUI.')
    parser.add_argument('--no-thinking', action='store_true', help='Disable thinking mode for all agents.')
    parser.add_argument('--prompt', type=str, help='Optional initial user message when running in CLI mode.')
    args = parser.parse_args()

    thinking = not args.no_thinking
    if args.gui:
        launch_gui(enable_thinking=thinking)
    else:
        run_cli_chat(query=args.prompt, enable_thinking=thinking)
