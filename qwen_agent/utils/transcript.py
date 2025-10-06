import json
import os
import threading
import time
from datetime import datetime

from qwen_agent.utils.redaction import redact
from qwen_agent.settings import DEFAULT_WORKSPACE

_lock = threading.Lock()


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def _default_path() -> str:
    root = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', DEFAULT_WORKSPACE)
    logdir = os.path.join(root, 'logs')
    os.makedirs(logdir, exist_ok=True)
    day = datetime.utcnow().strftime('%Y%m%d')
    return os.path.join(logdir, f'transcript-{day}.jsonl')


def append_event(event: dict, path: str | None = None):
    try:
        path = path or os.getenv('NOVA_TRANSCRIPT_FILE') or _default_path()
        # redact string fields
        redacted = {}
        for k, v in event.items():
            if isinstance(v, str):
                redacted[k] = redact(v)
            else:
                redacted[k] = v
        line = json.dumps(redacted, ensure_ascii=False)
        _ensure_dir(path)
        with _lock:
            with open(path, 'a', encoding='utf-8') as fp:
                fp.write(line + '\n')
    except Exception:
        # best effort; do not crash caller
        pass

