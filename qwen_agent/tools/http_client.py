import os
import json
import time
from typing import Dict, Optional, Union

import requests

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import json_dumps_pretty


@register_tool('http_client')
class HTTPClient(BaseTool):
    description = 'HTTP(S) client: GET/POST/PUT/DELETE/PATCH/HEAD, supports download to file.'
    parameters = {
        'type': 'object',
        'properties': {
            'method': {'type': 'string', 'enum': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD']},
            'url': {'type': 'string'},
            'headers': {'type': 'object'},
            'params': {'type': 'object'},
            'json': {'type': 'object'},
            'data': {'type': 'string'},
            'timeout': {'type': 'number'},
            'save_to': {'type': 'string', 'description': 'If set, stream body to this file path.'},
            'verify_ssl': {'type': 'boolean', 'default': True},
        },
        'required': ['method', 'url']
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        method = p['method'].upper()
        url = p['url']
        headers = p.get('headers') or {}
        query = p.get('params') or {}
        json_body = p.get('json')
        data_body = p.get('data')
        timeout = p.get('timeout')
        save_to = p.get('save_to')
        verify_ssl = bool(p.get('verify_ssl', True))

        started = time.time()
        try:
            if save_to:
                os.makedirs(os.path.dirname(save_to) or '.', exist_ok=True)
                with requests.request(method, url, headers=headers, params=query, json=json_body, data=data_body,
                                      timeout=timeout, stream=True, verify=verify_ssl) as r:
                    r.raise_for_status()
                    with open(save_to, 'wb') as fp:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                fp.write(chunk)
                took = time.time() - started
                return json_dumps_pretty({'status': 'ok', 'downloaded_to': save_to, 'took_s': took, 'code': 200})

            r = requests.request(method, url, headers=headers, params=query, json=json_body, data=data_body,
                                  timeout=timeout, verify=verify_ssl)
            took = time.time() - started
            info = {
                'code': r.status_code,
                'took_s': took,
                'headers': dict(r.headers),
            }
            # Avoid returning massive bodies; return full text up to 512KB
            text = r.text
            if text and len(text) > 512 * 1024:
                text = text[:512 * 1024] + '\n...[truncated]'
            info['body'] = text
            return json_dumps_pretty(info)
        except requests.RequestException as ex:
            return json_dumps_pretty({'error': 'http_error', 'message': str(ex)})

