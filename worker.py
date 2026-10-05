"""Version 1, newline-delimited JSON RPC. stdout is protocol only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import threading
from service import Service, BusyError
from store import ConflictError

LIMIT = 20_000_000

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--rustc')
    args = parser.parse_args()
    service = Service(args.data_dir, args.rustc)
    output_lock, tasks_lock = threading.Lock(), threading.Lock()
    tasks = {}
    pool = ThreadPoolExecutor(max_workers=4)

    def reply(rid, result=None, error=None):
        payload = dict(version=1, id=rid)
        payload['error' if error else 'result'] = error if error else result
        with output_lock:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + '\n')
            sys.stdout.flush()

    def dispatch(req, event):
        rid = req['id']
        try:
            result = service.call(req['method'], req.get('params'), cancel=event)
            reply(rid, result=result)
        except (ValueError, TypeError, KeyError) as e:
            code = 'conflict' if isinstance(e, ConflictError) else 'busy' if isinstance(e, BusyError) else 'invalid'
            reply(rid, error=dict(code=code, message=str(e)))
        except Exception as e:
            print(f'Worker error: {type(e).__name__}: {e}', file=sys.stderr)
            reply(rid, error=dict(code='internal', message='核心操作失败，请检查 Seagull 输出日志'))
        finally:
            with tasks_lock: tasks.pop(rid, None)

    try:
        while True:
            line = sys.stdin.buffer.readline(LIMIT + 1)
            if not line: break
            rid = None
            try:
                if len(line) > LIMIT:
                    while not line.endswith(b'\n'):
                        line = sys.stdin.buffer.readline(LIMIT + 1)
                        if not line: break
                    raise ValueError('消息超过 20 MB')
                req = json.loads(line)
                if not isinstance(req, dict): raise ValueError('请求结构错误')
                rid = req.get('id')
                if not isinstance(rid, str) or not rid or len(rid) > 100: raise ValueError('请求 ID 错误')
                if req.get('version') != 1: raise ValueError('协议版本不支持')
                if not isinstance(req.get('method'), str): raise ValueError('操作格式错误')
                if req['method'] == 'cancel':
                    target = req.get('params', {}).get('request_id')
                    with tasks_lock:
                        event = tasks.get(target)
                        if event: event.set()
                    reply(rid, result=dict(cancelled=bool(event)))
                    continue
                with tasks_lock:
                    if rid in tasks: raise ValueError('请求 ID 重复')
                    event = threading.Event()
                    tasks[rid] = event
                pool.submit(dispatch, req, event)
            except (ValueError, TypeError, AttributeError) as e:
                reply(rid, error=dict(code='invalid', message=str(e)))
    finally:
        with tasks_lock:
            for event in tasks.values(): event.set()
        pool.shutdown(wait=True)

if __name__ == '__main__': main()
