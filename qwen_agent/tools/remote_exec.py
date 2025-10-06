import json
import os
import subprocess
import time
from typing import Dict, Optional, Union

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import json_dumps_pretty


@register_tool('remote_exec')
class RemoteExec(BaseTool):
    description = 'Execute commands on remote hosts over SSH; optional file transfer via scp.'
    parameters = {
        'type': 'object',
        'properties': {
            'host': {'type': 'string', 'description': 'Remote hostname or IP.'},
            'user': {'type': 'string', 'description': 'SSH username (optional if using config).'},
            'port': {'type': 'number', 'description': 'SSH port (default 22).'},
            'keyfile': {'type': 'string', 'description': 'Path to private key file (if needed).'},
            'known_hosts': {'type': 'string', 'description': 'Path to known_hosts file (optional).'},
            'cmd': {'type': 'string', 'description': 'Shell command to run remotely.'},
            'timeout': {'type': 'number', 'description': 'Timeout seconds (0 or omit for none).'},
            'op': {'type': 'string', 'enum': ['exec','upload','download'], 'description': 'Operation type.'},
            'local_path': {'type': 'string', 'description': 'Local path for upload/download.'},
            'remote_path': {'type': 'string', 'description': 'Remote path for upload/download.'}
        },
        'required': ['host', 'op']
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        host = p['host']
        user = p.get('user')
        port = int(p.get('port', 22))
        keyfile = p.get('keyfile')
        known_hosts = p.get('known_hosts')
        op = p.get('op', 'exec')
        timeout = p.get('timeout')

        base_ssh = ['ssh', '-p', str(port), '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new']
        if keyfile:
            base_ssh += ['-i', keyfile]
        if known_hosts:
            base_ssh += ['-o', f'UserKnownHostsFile={known_hosts}']
        target = f'{user+"@" if user else ""}{host}'

        if op == 'exec':
            cmd = p.get('cmd') or 'true'
            started = time.time()
            try:
                cp = subprocess.run(base_ssh + [target, cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, timeout=timeout if (timeout and timeout > 0) else None)
                return json_dumps_pretty({
                    'exit_code': cp.returncode,
                    'stdout': cp.stdout,
                    'stderr': cp.stderr,
                    'took_s': time.time() - started
                })
            except subprocess.TimeoutExpired as ex:
                return json_dumps_pretty({'error': 'timeout', 'timeout': timeout})

        if op in ('upload', 'download'):
            local_path = p.get('local_path')
            remote_path = p.get('remote_path')
            if not local_path or not remote_path:
                return json_dumps_pretty({'error': 'missing_paths'})
            scp = ['scp', '-P', str(port)]
            if keyfile:
                scp += ['-i', keyfile]
            if known_hosts:
                scp += ['-o', f'UserKnownHostsFile={known_hosts}', '-o', 'StrictHostKeyChecking=accept-new']
            try:
                if op == 'upload':
                    cp = subprocess.run(scp + [local_path, f'{target}:{remote_path}'], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, timeout=timeout if (timeout and timeout > 0) else None)
                else:
                    cp = subprocess.run(scp + [f'{target}:{remote_path}', local_path], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, timeout=timeout if (timeout and timeout > 0) else None)
                return json_dumps_pretty({'exit_code': cp.returncode, 'stdout': cp.stdout, 'stderr': cp.stderr})
            except subprocess.TimeoutExpired:
                return json_dumps_pretty({'error': 'timeout', 'timeout': timeout})

        return json_dumps_pretty({'error': 'unsupported_op', 'op': op})

