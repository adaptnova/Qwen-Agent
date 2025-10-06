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
        if provider == 'clickhouse':
            return self._clickhouse(profile, op, payload)
        if provider == 'neo4j':
            return self._neo4j(profile, op, payload)
        if provider == 'weaviate':
            return self._weaviate(profile, op, payload)
        if provider == 'meilisearch':
            return self._meilisearch(profile, op, payload)
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

    def _clickhouse(self, profile: str, op: str, payload: Dict) -> str:
        env_path = f'/data/secrets/{profile or "CLICKHOUSE_MAIN"}.env'
        env = _read_env_file(env_path)
        # Prefer HTTP interface
        base = env.get('CLICKHOUSE_URL') or os.getenv('CLICKHOUSE_URL', 'http://127.0.0.1:8123')
        user = env.get('CLICKHOUSE_USER') or os.getenv('CLICKHOUSE_USER')
        password = env.get('CLICKHOUSE_PASSWORD') or os.getenv('CLICKHOUSE_PASSWORD')
        database = env.get('CLICKHOUSE_DATABASE') or os.getenv('CLICKHOUSE_DATABASE')
        try:
            import requests
            sql = payload.get('sql')
            if not sql:
                return json_dumps_pretty({'error': 'missing_sql'})
            params = {}
            if database:
                params['database'] = database
            r = requests.post(base, params=params, data=sql.encode('utf-8'), auth=(user, password) if user or password else None)
            if r.headers.get('content-type', '').startswith('application/json'):
                body = r.json()
            else:
                body = r.text
            return json_dumps_pretty({'code': r.status_code, 'body': body})
        except Exception as ex:
            return json_dumps_pretty({'error': 'clickhouse_error', 'message': str(ex)})

    def _neo4j(self, profile: str, op: str, payload: Dict) -> str:
        env_path = f'/data/secrets/{profile or "NEO4J_MAIN"}.env'
        env = _read_env_file(env_path)
        url = env.get('NEO4J_URL') or os.getenv('NEO4J_URL', 'neo4j://127.0.0.1:7687')
        user = env.get('NEO4J_USER') or os.getenv('NEO4J_USER')
        password = env.get('NEO4J_PASSWORD') or os.getenv('NEO4J_PASSWORD')
        try:
            from neo4j import GraphDatabase
        except Exception as ex:
            return json_dumps_pretty({'error': 'missing_dependency', 'package': 'neo4j', 'message': str(ex)})
        query = payload.get('cypher') or payload.get('query')
        params = payload.get('params') or {}
        if not query:
            return json_dumps_pretty({'error': 'missing_cypher'})
        try:
            driver = GraphDatabase.driver(url, auth=(user, password) if user or password else None)
            with driver.session() as session:
                res = session.run(query, **params)
                records = [r.data() for r in res]
            driver.close()
            return json_dumps_pretty({'rows': records, 'rowcount': len(records)})
        except Exception as ex:
            return json_dumps_pretty({'error': 'neo4j_error', 'message': str(ex)})

    def _weaviate(self, profile: str, op: str, payload: Dict) -> str:
        env_path = f'/data/secrets/{profile or "WEAVIATE_MAIN"}.env'
        env = _read_env_file(env_path)
        base = env.get('WEAVIATE_URL') or os.getenv('WEAVIATE_URL', 'http://127.0.0.1:8080')
        api_key = env.get('WEAVIATE_API_KEY') or os.getenv('WEAVIATE_API_KEY')
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        try:
            import requests
            if op == 'graphql':
                query = payload.get('query')
                if not query:
                    return json_dumps_pretty({'error': 'missing_query'})
                r = requests.post(f'{base}/v1/graphql', headers=headers, json={'query': query})
                return json_dumps_pretty({'code': r.status_code, 'body': self._safe_json(r)})
            elif op == 'objects_create':
                obj = payload.get('object')
                if not obj:
                    return json_dumps_pretty({'error': 'missing_object'})
                r = requests.post(f'{base}/v1/objects', headers=headers, json=obj)
                return json_dumps_pretty({'code': r.status_code, 'body': self._safe_json(r)})
            elif op == 'schema_put':
                cls = payload.get('class')
                if not cls:
                    return json_dumps_pretty({'error': 'missing_class'})
                r = requests.post(f'{base}/v1/schema/classes', headers=headers, json=cls)
                return json_dumps_pretty({'code': r.status_code, 'body': self._safe_json(r)})
            else:
                return json_dumps_pretty({'error': 'unsupported_op', 'op': op})
        except Exception as ex:
            return json_dumps_pretty({'error': 'weaviate_error', 'message': str(ex)})

    def _meilisearch(self, profile: str, op: str, payload: Dict) -> str:
        env_path = f'/data/secrets/{profile or "MEILI_MAIN"}.env'
        env = _read_env_file(env_path)
        base = env.get('MEILI_URL') or os.getenv('MEILI_URL', 'http://127.0.0.1:7700')
        key = env.get('MEILI_API_KEY') or os.getenv('MEILI_API_KEY')
        headers = {'Content-Type': 'application/json'}
        if key:
            headers['X-Meili-API-Key'] = key
        try:
            import requests
            if op == 'index_create':
                uid = payload['uid']
                primary_key = payload.get('primaryKey')
                body = {'uid': uid}
                if primary_key:
                    body['primaryKey'] = primary_key
                r = requests.post(f'{base}/indexes', headers=headers, json=body)
                return json_dumps_pretty({'code': r.status_code, 'body': self._safe_json(r)})
            elif op == 'add_documents':
                uid = payload['uid']
                docs = payload['documents']
                r = requests.post(f'{base}/indexes/{uid}/documents', headers=headers, json=docs)
                return json_dumps_pretty({'code': r.status_code, 'body': self._safe_json(r)})
            elif op == 'search':
                uid = payload['uid']
                q = payload.get('q', '')
                r = requests.post(f'{base}/indexes/{uid}/search', headers=headers, json={'q': q})
                return json_dumps_pretty({'code': r.status_code, 'body': self._safe_json(r)})
            else:
                return json_dumps_pretty({'error': 'unsupported_op', 'op': op})
        except Exception as ex:
            return json_dumps_pretty({'error': 'meili_error', 'message': str(ex)})
