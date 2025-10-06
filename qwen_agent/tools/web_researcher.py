import json
import os
from typing import Dict, List, Union

import requests

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import json_dumps_pretty


@register_tool('web_researcher')
class WebResearcher(BaseTool):
    description = 'Search the web, fetch top results, and extract readable text.'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {'type': 'string'},
            'provider': {'type': 'string', 'enum': ['serper', 'tavily']},
            'num_results': {'type': 'number', 'default': 5},
            'max_chars': {'type': 'number', 'default': 5000}
        },
        'required': ['query']
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        query = p['query']
        provider = (p.get('provider') or 'serper').lower()
        num = int(p.get('num_results', 5))
        max_chars = int(p.get('max_chars', 5000))

        # 1) search
        try:
            from qwen_agent.tools.search_tool import SearchTool
            search = SearchTool()
            raw = search.call({'provider': provider, 'query': query, 'num_results': num})
            # Parse back from the markdown-like list to get URLs
            items = []
            for block in raw.strip('`\n').split('\n\n'):
                lines = block.split('\n')
                if len(lines) >= 3:
                    title = lines[0].strip()
                    snippet = lines[1].strip()
                    url = lines[2].strip()
                    items.append({'title': title, 'snippet': snippet, 'url': url})
        except Exception as ex:
            return json_dumps_pretty({'error': 'search_failed', 'message': str(ex)})

        # 2) fetch and extract
        results: List[Dict] = []
        for it in items:
            url = it['url']
            text = ''
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                html = r.text
                text = self._html_to_text(html)
                if len(text) > max_chars:
                    text = text[:max_chars] + '\n...[truncated]'
            except Exception:
                text = ''
            results.append({'title': it['title'], 'url': url, 'snippet': it['snippet'], 'text': text})

        return json_dumps_pretty({'query': query, 'provider': provider, 'results': results})

    @staticmethod
    def _html_to_text(html: str) -> str:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            # Remove script/style
            for tag in soup(['script', 'style', 'noscript']):
                tag.extract()
            return soup.get_text(separator='\n')
        except Exception:
            # Fallback: very rough tag strip
            import re
            clean = re.sub(r'<script[\s\S]*?</script>', ' ', html, flags=re.I)
            clean = re.sub(r'<style[\s\S]*?</style>', ' ', clean, flags=re.I)
            clean = re.sub(r'<[^>]+>', ' ', clean)
            return re.sub(r'\n\s*\n+', '\n', clean)

