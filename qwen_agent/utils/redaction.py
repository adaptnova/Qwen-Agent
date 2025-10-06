import os
import re
import time
from typing import Dict, List

_CACHE = {
    'compiled': None,
    'ts': 0.0,
}


def _load_secret_values() -> List[str]:
    values: List[str] = []
    secrets_dir = os.getenv('NOVA_SECRETS_DIR', '/data/secrets')
    try:
        if os.path.isdir(secrets_dir):
            for name in os.listdir(secrets_dir):
                path = os.path.join(secrets_dir, name)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, 'r', encoding='utf-8') as fp:
                        for line in fp:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            if '=' in line:
                                _, v = line.split('=', 1)
                                v = v.strip().strip('"')
                                if v and v not in values:
                                    values.append(v)
                except Exception:
                    continue
    except Exception:
        pass

    # Common env keys as fallback
    for k in [
        'SERPER_API_KEY', 'TAVILY_API_KEY', 'PGPASSWORD', 'ES_APIKEY', 'ES_PASSWORD',
        'CLICKHOUSE_PASSWORD', 'NEO4J_PASSWORD', 'WEAVIATE_API_KEY', 'MEILI_API_KEY',
        'OPENAI_API_KEY', 'DASHSCOPE_API_KEY'
    ]:
        v = os.getenv(k)
        if v and v not in values:
            values.append(v)
    return values


def _compile_patterns(values: List[str]):
    patterns = []
    for v in values:
        if not v or len(v) < 6:
            continue
        try:
            pat = re.compile(re.escape(v))
            masked = _mask(v)
            patterns.append((pat, masked))
        except re.error:
            continue
    return patterns


def _mask(s: str) -> str:
    if len(s) <= 8:
        return '****'
    return s[:2] + '***' + s[-4:]


def _get_compiled():
    now = time.time()
    if _CACHE['compiled'] is None or now - _CACHE['ts'] > 60:
        vals = _load_secret_values()
        _CACHE['compiled'] = _compile_patterns(vals)
        _CACHE['ts'] = now
    return _CACHE['compiled']


def redact(text: str) -> str:
    if not text:
        return text
    try:
        patterns = _get_compiled()
        red = text
        for pat, repl in patterns:
            red = pat.sub(repl, red)
        return red
    except Exception:
        return text

