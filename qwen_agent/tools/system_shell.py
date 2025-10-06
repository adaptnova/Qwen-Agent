import json
import os
import shlex
import subprocess
import time
import uuid
from typing import Dict, Optional, Union

from qwen_agent.settings import DEFAULT_WORKSPACE
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import json_dumps_pretty


@register_tool('system_shell')
class SystemShell(BaseTool):
    """
    Execute arbitrary shell commands with root privileges.
    Supports foreground (capture output) and background (return PID and log file paths).
    """

    description = 'Run any shell command as root; background supported.'
    parameters = {
        'type': 'object',
        'properties': {
            'cmd': {
                'type': 'string',
                'description': 'The shell command to execute.'
            },
            'cwd': {
                'type': 'string',
                'description': 'Working directory (absolute or relative).'
            },
            'env': {
                'type': 'object',
                'description': 'Environment variables to inject (name->value).'
            },
            'timeout': {
                'type': 'number',
                'description': 'Seconds before abort (0 or missing = no timeout).'
            },
            'background': {
                'type': 'boolean',
                'description': 'Run in background and return PID/log paths.'
            }
        },
        'required': ['cmd']
    }

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.base_runs = os.path.join(DEFAULT_WORKSPACE, 'runs', 'system_shell')
        os.makedirs(self.base_runs, exist_ok=True)

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        cmd: str = p['cmd']
        cwd: Optional[str] = p.get('cwd')
        env_extra: Dict[str, str] = p.get('env', {}) or {}
        timeout: Optional[float] = p.get('timeout')
        background: bool = bool(p.get('background', False))

        env = os.environ.copy()
        env.update({k: str(v) for k, v in env_extra.items()})

        started_at = time.time()
        if background:
            run_id = str(uuid.uuid4())
            run_dir = os.path.join(self.base_runs, run_id)
            os.makedirs(run_dir, exist_ok=True)
            stdout_path = os.path.join(run_dir, 'stdout.log')
            stderr_path = os.path.join(run_dir, 'stderr.log')
            with open(stdout_path, 'wb') as out, open(stderr_path, 'wb') as err:
                proc = subprocess.Popen(
                    cmd if isinstance(cmd, list) else ['/bin/bash', '-lc', cmd],
                    cwd=cwd or None,
                    env=env,
                    stdout=out,
                    stderr=err,
                )
            meta = {
                'pid': proc.pid,
                'cmd': cmd,
                'cwd': cwd or os.getcwd(),
                'stdout': stdout_path,
                'stderr': stderr_path,
                'started_at': started_at,
                'run_dir': run_dir,
            }
            with open(os.path.join(run_dir, 'meta.json'), 'w', encoding='utf-8') as fp:
                fp.write(json_dumps_pretty(meta))
            return json_dumps_pretty({'status': 'started', **meta})

        try:
            cp = subprocess.run(
                cmd if isinstance(cmd, list) else ['/bin/bash', '-lc', cmd],
                cwd=cwd or None,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout if (timeout and timeout > 0) else None,
                text=True,
            )
            finished_at = time.time()
            return json_dumps_pretty({
                'exit_code': cp.returncode,
                'started_at': started_at,
                'finished_at': finished_at,
                'stdout': cp.stdout,
                'stderr': cp.stderr,
            })
        except subprocess.TimeoutExpired as ex:
            return json_dumps_pretty({
                'error': 'timeout',
                'timeout': timeout,
                'stdout': ex.stdout.decode('utf-8', errors='ignore') if ex.stdout else '',
                'stderr': ex.stderr.decode('utf-8', errors='ignore') if ex.stderr else '',
            })

