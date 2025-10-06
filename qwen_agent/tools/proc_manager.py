import json
import os
import signal
import subprocess
from typing import Dict, Union

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import json_dumps_pretty


@register_tool('proc_manager')
class ProcManager(BaseTool):
    description = 'Process management: ps, kill/terminate, renice, list_ports, tail.'
    parameters = {
        'type': 'object',
        'properties': {
            'action': {
                'type': 'string',
                'enum': ['ps', 'kill', 'terminate', 'renice', 'list_ports', 'tail']
            },
            'pid': {'type': 'number'},
            'signal': {'type': 'string'},
            'nice': {'type': 'number'},
            'path': {'type': 'string'},
            'lines': {'type': 'number'}
        },
        'required': ['action']
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        action = p['action']

        if action == 'ps':
            # Fallback to ps if psutil is not available
            cmd = ['bash', '-lc', "ps -eo pid,comm,pcpu,pmem,etime,stat,ppid,args --no-headers | head -n 500"]
            cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return cp.stdout or cp.stderr

        if action in ('kill', 'terminate'):
            pid = int(p.get('pid', -1))
            if pid <= 1:
                return json_dumps_pretty({'error': 'invalid_pid'})
            sig_name = p.get('signal') or ('SIGKILL' if action == 'kill' else 'SIGTERM')
            sig = getattr(signal, sig_name, signal.SIGKILL if action == 'kill' else signal.SIGTERM)
            try:
                os.kill(pid, sig)
                return json_dumps_pretty({'status': 'ok', 'pid': pid, 'signal': sig_name})
            except ProcessLookupError:
                return json_dumps_pretty({'error': 'not_found', 'pid': pid})

        if action == 'renice':
            pid = int(p.get('pid', -1))
            nice = int(p.get('nice', 0))
            if pid <= 1:
                return json_dumps_pretty({'error': 'invalid_pid'})
            try:
                os.setpriority(os.PRIO_PROCESS, pid, nice)
                return json_dumps_pretty({'status': 'ok', 'pid': pid, 'nice': nice})
            except Exception as ex:
                return json_dumps_pretty({'error': 'renice_failed', 'message': str(ex)})

        if action == 'list_ports':
            cmd = ['bash', '-lc', "ss -lntp | head -n 500 || netstat -tulpn | head -n 500"]
            cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return cp.stdout or cp.stderr

        if action == 'tail':
            path = p.get('path')
            n = int(p.get('lines', 200))
            if not path or not os.path.exists(path):
                return json_dumps_pretty({'error': 'not_found', 'path': path})
            try:
                # Efficient tail for reasonably sized files
                with open(path, 'rb') as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    block = 4096
                    data = b''
                    while size > 0 and data.count(b'\n') <= n:
                        step = block if size >= block else size
                        f.seek(-step, os.SEEK_CUR)
                        data = f.read(step) + data
                        f.seek(-step, os.SEEK_CUR)
                        size -= step
                lines = data.splitlines()[-n:]
                return '\n'.join(x.decode('utf-8', errors='ignore') for x in lines)
            except Exception as ex:
                return json_dumps_pretty({'error': 'tail_failed', 'message': str(ex)})

        return json_dumps_pretty({'error': 'unsupported_action', 'action': action})

