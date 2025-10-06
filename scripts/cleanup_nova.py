#!/usr/bin/env python3
import os
import time
import shutil

ROOT = os.getenv('QWEN_AGENT_DEFAULT_WORKSPACE', '/data/nova')
TTL_DAYS = int(os.getenv('NOVA_CLEAN_TTL_DAYS', '14'))


def older_than(path: str, days: int) -> bool:
    try:
        st = os.stat(path)
        return (time.time() - st.st_mtime) > days * 86400
    except Exception:
        return False


def clean_dir(path: str, days: int):
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        p = os.path.join(path, name)
        try:
            if older_than(p, days):
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    os.remove(p)
        except Exception:
            continue


def main():
    tmp = os.path.join(ROOT, 'tmp')
    runs = os.path.join(ROOT, 'runs')
    datasets = os.path.join(ROOT, 'datasets')
    clean_dir(tmp, TTL_DAYS)
    clean_dir(runs, TTL_DAYS)
    # do not aggressively delete datasets by default; comment out below if desired
    # clean_dir(datasets, TTL_DAYS)


if __name__ == '__main__':
    main()

