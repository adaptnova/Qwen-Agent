import os
import time
from typing import List

from qwen_agent.agents import Assistant
from qwen_agent.agents.router import Router
from qwen_agent.llm.schema import Message


CODER_KEYWORDS = [
    'code', 'python', 'bug', 'function', 'class', 'traceback', 'stack trace', 'syntax', 'compile',
    'exception', 'flake8', 'pytest', 'unit test', 'refactor', 'diff', 'pull request', 'commit'
]


def _default_general_tools() -> List[str]:
    return [
        'system_shell', 'fs_admin', 'http_client', 'proc_manager', 'search_tool', 'web_researcher',
        'sql_tool', 'python_executor', 'code_interpreter', 'web_search', 'retrieval', 'remote_exec'
    ]


def _coder_tools() -> List[str]:
    return ['python_executor', 'system_shell', 'proc_manager', 'fs_admin', 'sql_tool', 'remote_exec']


def build_generalist_agent() -> Assistant:
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
        }
    }
    system_prompt = (
        'You are Nova, the generalist operator with full system access. Use any tools you need. '
        'If a request requires deep coding changes or debugging, you may call on the Coder specialist.'
    )
    return Assistant(function_list=_default_general_tools(), llm=llm_cfg, system_message=system_prompt, name='Nova')


def build_coder_agent() -> Assistant:
    coder_server = os.getenv('NOVA_CODER_LLM_SERVER', 'http://127.0.0.1:8010/v1')
    coder_model = os.getenv('NOVA_CODER_LLM_MODEL', 'Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8')
    llm_cfg = {
        'model': coder_model,
        'model_type': 'oai',
        'model_server': coder_server,
        'generate_cfg': {
            'parallel_function_calls': True,
            'function_choice': 'auto',
            'use_raw_api': True,
        }
    }
    system_prompt = (
        'You are Nova-Coder, a specialist focused on software engineering tasks. Provide precise, executable code, '
        'debug complex issues, and run tests via the available tools. If the task is outside coding, defer to Nova.'
    )
    return Assistant(function_list=_coder_tools(), llm=llm_cfg, system_message=system_prompt, name='Nova-Coder')


class NovaRouter(Router):

    PROMPT = '''You have two assistants:
- Nova: full-spectrum operations, reasoning, research, multimodal tasks.
- Nova-Coder: expert in programming, debugging, test automation, repository analysis.

If the user request clearly revolves around coding (writing/modifying code, debugging, unit tests, build pipelines), call Nova-Coder.
Otherwise, handle the task yourself as Nova.

When you choose a specialist, reply exactly with:
Call: <assistant name>
Reply: <leave blank>
'''

    def __init__(self, agents: List[Assistant]):
        llm_server = os.getenv('NOVA_ROUTER_LLM_SERVER', os.getenv('NOVA_LLM_SERVER', 'http://10.0.1.1:18000/v1'))
        llm_model = os.getenv('NOVA_ROUTER_LLM_MODEL', os.getenv('NOVA_LLM_MODEL', 'Qwen/Qwen3-VL-30B-A3B-Thinking-FP8'))
        llm_cfg = {
            'model': llm_model,
            'model_type': 'oai',
            'model_server': llm_server,
            'generate_cfg': {
                'parallel_function_calls': False,
                'use_raw_api': True,
            }
        }
        super().__init__(function_list=_default_general_tools(), llm=llm_cfg, agents=agents, name='Nova-Router')
        self.system_message = self.PROMPT.format()


def detect_code_intent(messages: List[Message]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    content = last.content if isinstance(last.content, str) else ''.join(x.text or '' for x in last.content if hasattr(x, 'text'))
    content_lower = content.lower()
    for kw in CODER_KEYWORDS:
        if kw in content_lower:
            return True
    if '```' in content_lower:
        return True
    return False


def run_router(prompt: str):
    general = build_generalist_agent()
    coder = build_coder_agent()
    router = NovaRouter([general, coder])
    messages = [Message(role='user', content=prompt)]
    # heuristic short-circuit
    if detect_code_intent(messages):
        agent = coder
        model_tag = 'coder'
    else:
        agent = router
        model_tag = 'router'

    final = None
    for response in agent.run(messages):
        final = response
    text = final[-1].content if final else ''
    try:
        from qwen_agent.utils.transcript import append_event
        append_event({'ts': time.time(), 'event': 'model_switch', 'model': model_tag, 'prompt': prompt[:500], 'response_preview': text[:500] if isinstance(text, str) else str(text)[:500]})
    except Exception:
        pass
    return text


if __name__ == '__main__':
    sample = 'Debug this Python function that throws a ValueError when processing JSON.'
    result = run_router(sample)
    print(result)
