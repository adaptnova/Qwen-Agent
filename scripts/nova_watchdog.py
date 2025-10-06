#!/usr/bin/env python3
import os
import socket
import subprocess
import sys
import json
import time

SOCK_PATH = os.environ.get('NOVA_WATCHDOG_SOCK', '/run/nova_watchdog.sock')
RUNS_DIR = os.environ.get('NOVA_RUNS_DIR', '/data/nova/runs/system_shell')


def kill_pid(pid: int):
    if pid <= 1:
        return
    try:
        os.kill(pid, 15)
        time.sleep(0.5)
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    except PermissionError:
        pass


def kill_known_background_jobs():
    if not os.path.isdir(RUNS_DIR):
        return
    for name in os.listdir(RUNS_DIR):
        meta = os.path.join(RUNS_DIR, name, 'meta.json')
        if not os.path.exists(meta):
            continue
        try:
            with open(meta, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            pid = int(data.get('pid', 0))
            kill_pid(pid)
        except Exception:
            continue


def kill_agent_tree():
    # Best-effort pkill for typical processes; safe in disposable VM
    patterns = [
        'run_server.py',
        'qwen_server/assistant_server.py',
        'qwen_server/database_server.py',
        'qwen_server/workstation_server.py',
        'examples/nova_agent.py',
    ]
    for pat in patterns:
        subprocess.call(['bash', '-lc', f"pkill -9 -f '{pat}' || true"])  # nosec


def serve():
    # Remove stale socket
    if os.path.exists(SOCK_PATH):
        try:
            os.remove(SOCK_PATH)
        except Exception:
            pass
    sock_dir = os.path.dirname(SOCK_PATH) or '/run'
    os.makedirs(sock_dir, exist_ok=True)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCK_PATH)
    os.chmod(SOCK_PATH, 0o666)
    s.listen(5)
    while True:
        conn, _ = s.accept()
        try:
            data = conn.recv(4096).decode('utf-8', errors='ignore').strip()
            if not data:
                conn.close()
                continue
            if data.upper().startswith('STOP'):
                kill_known_background_jobs()
                kill_agent_tree()
                conn.sendall(b'OK\n')
            elif data.upper().startswith('PING'):
                conn.sendall(b'PONG\n')
            else:
                conn.sendall(b'UNKNOWN\n')
        finally:
            conn.close()


if __name__ == '__main__':
    try:
        serve()
    except KeyboardInterrupt:
        sys.exit(0)

