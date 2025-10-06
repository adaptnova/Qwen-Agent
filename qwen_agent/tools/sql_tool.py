import os
import json
from typing import Dict, Union

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


@register_tool('sql_tool')
class SQLTool(BaseTool):
    description = 'Interact with databases: postgres, clickhouse, neo4j, weaviate, meilisearch, elasticsearch.'
    parameters = {
        'type': 'object',
        'properties': {
            'provider': {
                'type': 'string',
                'enum': ['postgres', 'clickhouse', 'neo4j', 'weaviate', 'meilisearch', 'elasticsearch']
            },
            'profile': {
                'type': 'string',
                'description': 'Connection profile name mapping to /data/secrets/<PROFILE>.env'
            },
            'op': {'type': 'string', 'description': 'Operation, e.g., query/insert/upsert/search/admin'},
            'payload': {'type': 'object', 'description': 'Operation args; e.g., SQL/Cypher/JSON body.'},
            'timeout': {'type': 'number'}
        },
        'required': ['provider', 'op', 'payload']
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        provider = p['provider']
        profile = p.get('profile')
        op = p['op']
        payload = p.get('payload') or {}

        if provider == 'postgres':
            return self._postgres(profile, op, payload)
        if provider == 'elasticsearch':
            return self._elasticsearch(profile, op, payload)
        if provider in ('clickhouse', 'neo4j', 'weaviate', 'meilisearch'):
            return json_dumps_pretty({'error': 'provider_not_implemented', 'provider': provider})
        return json_dumps_pretty({'error': 'unsupported_provider', 'provider': provider})

    def _postgres(self, profile: str, op: str, payload: Dict) -> str:
        env_path = f'/data/secrets/{profile or "POSTGRES_MAIN"}.env'
        env = _read_env_file(env_path)
        host = env.get('PGHOST') or os.getenv('PGHOST', '127.0.0.1')
        port = int(env.get('PGPORT') or os.getenv('PGPORT', '5432'))
        user = env.get('PGUSER') or os.getenv('PGUSER')
        password = env.get('PGPASSWORD') or os.getenv('PGPASSWORD')
        database = env.get('PGDATABASE') or os.getenv('PGDATABASE')
        try:
            import psycopg
        except Exception as ex:
            return json_dumps_pretty({'error': 'missing_dependency', 'package': 'psycopg', 'message': str(ex)})

        dsn = f'host={host} port={port} user={user} password={password} dbname={database}'
        try:
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    if op == 'query':
                        sql = payload.get('sql')
                        params = payload.get('params')
                        cur.execute(sql, params)
                        rows = cur.fetchall() if cur.description else []
                        cols = [d[0] for d in cur.description] if cur.description else []
                        data = [dict(zip(cols, r)) for r in rows]
                        return json_dumps_pretty({'rows': data, 'rowcount': cur.rowcount})
                    elif op == 'execute':
                        sql = payload.get('sql')
                        params = payload.get('params')
                        cur.execute(sql, params)
                        conn.commit()
                        return json_dumps_pretty({'status': 'ok', 'rowcount': cur.rowcount})
                    else:
                        return json_dumps_pretty({'error': 'unsupported_op', 'op': op})
        except Exception as ex:
            return json_dumps_pretty({'error': 'postgres_error', 'message': str(ex)})

    def _elasticsearch(self, profile: str, op: str, payload: Dict) -> str:
        env_path = f'/data/secrets/{profile or "ELASTIC_MAIN"}.env'
        env = _read_env_file(env_path)
        base = env.get('ES_URL') or os.getenv('ES_URL', 'http://127.0.0.1:9200')
        apikey = env.get('ES_APIKEY') or os.getenv('ES_APIKEY')
        user = env.get('ES_USER') or os.getenv('ES_USER')
        passwd = env.get('ES_PASSWORD') or os.getenv('ES_PASSWORD')

        headers = {'Content-Type': 'application/json'}
        auth = None
        if apikey:
            headers['Authorization'] = f'ApiKey {apikey}'
        elif user and passwd:
            auth = (user, passwd)

        try:
            import requests
            if op == 'index':
                index = payload['index']
                doc = payload['doc']
                r = requests.post(f'{base}/{index}/_doc', headers=headers, auth=auth, json=doc)
                return json_dumps_pretty({'code': r.status_code, 'body': r.json()})
            elif op == 'search':
                index = payload['index']
                query = payload.get('query', {'match_all': {}})
                r = requests.get(f'{base}/{index}/_search', headers=headers, auth=auth, json={'query': query})
                return json_dumps_pretty({'code': r.status_code, 'body': r.json()})
            elif op == 'put_index':
                index = payload['index']
                body = payload.get('body', {})
                r = requests.put(f'{base}/{index}', headers=headers, auth=auth, json=body)
                return json_dumps_pretty({'code': r.status_code, 'body': self._safe_json(r)})
            else:
                return json_dumps_pretty({'error': 'unsupported_op', 'op': op})
        except Exception as ex:
            return json_dumps_pretty({'error': 'elastic_error', 'message': str(ex)})

    @staticmethod
    def _safe_json(r):
        try:
            return r.json()
        except Exception:
            return r.text

