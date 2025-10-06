import json
import os
from typing import Dict, Union

import requests

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import json_dumps_pretty


def _read_env_file(path: str) -> Dict[str, str]:
    env = {}
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            for line in fp:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip().strip('"')
    except Exception:
        pass
    return env


@register_tool('search_tool')
class SearchTool(BaseTool):
    description = 'Web search via Serper or Tavily; returns titles/snippets/links.'
    parameters = {
        'type': 'object',
        'properties': {
            'provider': {'type': 'string', 'enum': ['serper', 'tavily']},
            'query': {'type': 'string'},
            'num_results': {'type': 'number', 'default': 10}
        },
        'required': ['query']
    }

    def _serper(self, query: str, num: int) -> Dict:
        # Prefer env file at /data/secrets/SERPER.env, else env vars
        env = _read_env_file('/data/secrets/SERPER.env')
        api_key = env.get('SERPER_API_KEY') or os.getenv('SERPER_API_KEY')
        base_url = env.get('SERPER_URL') or os.getenv('SERPER_URL', 'https://google.serper.dev/search')
        if not api_key:
            raise ValueError('SERPER_API_KEY not configured')
        headers = {'Content-Type': 'application/json', 'X-API-KEY': api_key}
        payload = {'q': query, 'num': int(num) if num else 10}
        r = requests.post(base_url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        organic = data.get('organic', [])
        results = []
        for i, doc in enumerate(organic[:num], 1):
            results.append({
                'index': i,
                'title': doc.get('title', ''),
                'snippet': doc.get('snippet', ''),
                'url': doc.get('link', ''),
                'date': doc.get('date', '')
            })
        return {'provider': 'serper', 'results': results}

    def _tavily(self, query: str, num: int) -> Dict:
        env = _read_env_file('/data/secrets/TAVILY.env')
        api_key = env.get('TAVILY_API_KEY') or os.getenv('TAVILY_API_KEY')
        if not api_key:
            raise ValueError('TAVILY_API_KEY not configured')
        # Tavily API
        url = 'https://api.tavily.com/search'
        payload = {'api_key': api_key, 'query': query, 'search_depth': 'basic', 'max_results': int(num) if num else 10}
        r = requests.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        results = []
        for i, doc in enumerate(data.get('results', [])[:num], 1):
            results.append({'index': i, 'title': doc.get('title', ''), 'snippet': doc.get('content', ''), 'url': doc.get('url', '')})
        return {'provider': 'tavily', 'results': results}

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        provider = (p.get('provider') or 'serper').lower()
        query = p['query']
        num = int(p.get('num_results', 10))
        try:
            if provider == 'tavily':
                data = self._tavily(query, num)
            else:
                data = self._serper(query, num)
            # Pretty print as markdown-like listing
            lines = []
            for r in data['results']:
                title = r['title']
                snippet = r['snippet']
                url = r['url']
                lines.append(f"[{r['index']}] \"{title}\n{snippet}\"\n{url}")
            return '```\n' + '\n\n'.join(lines) + '\n```'
        except Exception as ex:
            return json_dumps_pretty({'error': 'search_failed', 'message': str(ex)})

