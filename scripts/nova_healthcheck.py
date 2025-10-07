#!/usr/bin/env python3
"""Comprehensive health check for the Nova stack."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests


def check_vllm(endpoint: str, model: str, api_key: str | None) -> dict:
    url = endpoint.rstrip('/') + '/chat/completions'
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': 'ping'}],
        'max_tokens': 8,
    }
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    start = time.time()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        latency = time.time() - start
        ok = resp.status_code == 200
        info = {'latency_ms': int(latency * 1000), 'status_code': resp.status_code}
        if ok:
            try:
                data = resp.json()
                info['id'] = data.get('id')
            except Exception:
                ok = False
        else:
            info['body'] = resp.text[:200]
        return {'ok': ok, 'detail': info}
    except Exception as ex:
        return {'ok': False, 'detail': {'error': str(ex)}}


def check_control_server(host: str, port: int) -> dict:
    base = f'http://{host}:{port}'
    try:
        resp = requests.get(f'{base}/health', timeout=5)
        ok = resp.status_code == 200 and resp.json().get('status') == 'ok'
        status_detail = resp.text
    except Exception as ex:
        return {'ok': False, 'detail': {'error': str(ex)}}

    try:
        status_resp = requests.get(f'{base}/status', timeout=5)
        qlen = status_resp.json().get('queue_len', '?') if status_resp.status_code == 200 else '?'
    except Exception:
        qlen = '?'
    return {'ok': ok, 'detail': {'health': status_detail, 'queue_len': qlen}}


def check_logs(workspace: str) -> dict:
    logdir = Path(workspace) / 'logs'
    if not logdir.exists():
        return {'ok': False, 'detail': {'error': f'{logdir} missing'}}
    transcripts = sorted(logdir.glob('transcript-*.jsonl'))
    if not transcripts:
        return {'ok': False, 'detail': {'error': 'no transcripts yet'}}
    latest = transcripts[-1]
    size = latest.stat().st_size
    return {'ok': size > 0, 'detail': {'path': str(latest), 'size_bytes': size}}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--control-host', default='127.0.0.1')
    ap.add_argument('--control-port', type=int, default=int(os.getenv('NOVA_CONTROL_PORT', '7125')))
    ap.add_argument('--workspace', default=os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova'))
    ap.add_argument('--endpoint', default=os.getenv('NOVA_LLM_SERVER', 'http://10.0.1.1:18000/v1'))
    ap.add_argument('--model', default=os.getenv('NOVA_LLM_MODEL', 'Qwen/Qwen3-VL-30B-A3B-Thinking-FP8'))
    ap.add_argument('--api-key', default=os.getenv('NOVA_LLM_API_KEY'))
    ap.add_argument('--json', action='store_true')
    return ap.parse_args()


def main():
    args = parse_args()
    results = {
        'vllm': check_vllm(args.endpoint, args.model, args.api_key),
        'control': check_control_server(args.control_host, args.control_port),
        'logs': check_logs(args.workspace),
    }

    coder_endpoint = os.getenv('NOVA_CODER_LLM_SERVER')
    coder_model = os.getenv('NOVA_CODER_LLM_MODEL')
    if coder_endpoint and coder_model:
        results['coder'] = check_vllm(coder_endpoint, coder_model, os.getenv('NOVA_CODER_LLM_API_KEY'))
    ok = all(v['ok'] for v in results.values())
    if args.json:
        print(json.dumps({'ok': ok, 'checks': results}, indent=2))
    else:
        for name, res in results.items():
            status = 'OK' if res['ok'] else 'FAIL'
            print(f"{name:<10} {status} {res['detail']}")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
