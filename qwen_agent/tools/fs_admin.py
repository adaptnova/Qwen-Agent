import json
import os
import shutil
import stat
from typing import Dict, Optional, Union

from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.utils import json_dumps_pretty, read_text_from_file, save_text_to_file


@register_tool('fs_admin')
class FSAdmin(BaseTool):
    description = 'Full filesystem operations: read/write/append/list/move/copy/mkdir/rmdir/chmod/chown/stat.'
    parameters = {
        'type': 'object',
        'properties': {
            'op': {
                'type': 'string',
                'enum': ['read', 'write', 'append', 'list', 'move', 'copy', 'mkdir', 'rmdir', 'chmod', 'chown', 'stat']
            },
            'path': {
                'type': 'string'
            },
            'path2': {
                'type': 'string',
                'description': 'Destination path for move/copy.'
            },
            'content': {
                'type': 'string',
                'description': 'Content for write/append.'
            },
            'mode': {
                'type': 'string',
                'description': 'Octal mode for chmod, e.g., 0755.'
            },
            'owner': {
                'type': 'string'
            },
            'group': {
                'type': 'string'
            }
        },
        'required': ['op', 'path']
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        p = self._verify_json_format_args(params)
        op = p['op']
        path = p['path']

        if op == 'read':
            data = read_text_from_file(path)
            return data

        if op == 'write':
            content = p.get('content', '')
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            save_text_to_file(path, content)
            return f'Wrote {len(content)} bytes to {path}'

        if op == 'append':
            content = p.get('content', '')
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'a', encoding='utf-8') as fp:
                fp.write(content)
            return f'Appended {len(content)} bytes to {path}'

        if op == 'list':
            if not os.path.exists(path):
                return json_dumps_pretty({'error': 'not_found', 'path': path})
            entries = []
            for name in os.listdir(path):
                pth = os.path.join(path, name)
                try:
                    st = os.lstat(pth)
                    entries.append({'name': name, 'is_dir': os.path.isdir(pth), 'size': st.st_size})
                except Exception:
                    entries.append({'name': name, 'error': 'stat_failed'})
            return json_dumps_pretty({'path': path, 'entries': entries})

        if op == 'move':
            dest = p.get('path2')
            if not dest:
                return json_dumps_pretty({'error': 'missing_path2'})
            os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
            shutil.move(path, dest)
            return f'Moved {path} to {dest}'

        if op == 'copy':
            dest = p.get('path2')
            if not dest:
                return json_dumps_pretty({'error': 'missing_path2'})
            os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
            if os.path.isdir(path):
                shutil.copytree(path, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(path, dest)
            return f'Copied {path} to {dest}'

        if op == 'mkdir':
            os.makedirs(path, exist_ok=True)
            return f'Created directory {path}'

        if op == 'rmdir':
            if os.path.isdir(path):
                shutil.rmtree(path)
                return f'Removed directory {path}'
            else:
                os.remove(path)
                return f'Removed file {path}'

        if op == 'chmod':
            mode_str = p.get('mode')
            if not mode_str:
                return json_dumps_pretty({'error': 'missing_mode'})
            os.chmod(path, int(mode_str, 8))
            return f'Chmod {mode_str} on {path}'

        if op == 'chown':
            owner = p.get('owner')
            group = p.get('group')
            uid = -1
            gid = -1
            if owner:
                try:
                    import pwd
                    uid = pwd.getpwnam(owner).pw_uid
                except Exception:
                    uid = int(owner)
            if group:
                try:
                    import grp
                    gid = grp.getgrnam(group).gr_gid
                except Exception:
                    gid = int(group)
            os.chown(path, uid, gid)
            return f'Chown {owner}:{group} on {path}'

        if op == 'stat':
            st = os.lstat(path)
            info = {
                'size': st.st_size,
                'mode': oct(stat.S_IMODE(st.st_mode)),
                'uid': st.st_uid,
                'gid': st.st_gid,
                'mtime': st.st_mtime,
                'ctime': st.st_ctime,
                'atime': st.st_atime,
                'is_dir': os.path.isdir(path),
                'is_file': os.path.isfile(path),
            }
            return json_dumps_pretty(info)

        return json_dumps_pretty({'error': 'unsupported_op', 'op': op})

