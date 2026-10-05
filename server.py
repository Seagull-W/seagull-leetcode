"""Loopback HTTP adapter for the shared personal practice core."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from service import Service, BusyError, problem_public, MASTERY
from store import ConflictError

ROOT = Path(__file__).resolve().parent

class AppServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, data_dir):
        super().__init__(address, Handler)
        self.service = Service(data_dir)
        self.store = self.service.store
        self.token = secrets.token_urlsafe(32)
        self.allowed_host = f'127.0.0.1:{self.server_address[1]}'
        self.origin = 'http://' + self.allowed_host

class Handler(BaseHTTPRequestHandler):
    server_version = 'Seagull/1.1'
    def log_message(self, fmt, *args): pass

    def reply(self, payload, status=200, kind='application/json; charset=utf-8', extra=None):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        for k, v in {'Content-Type': kind, 'Content-Length': str(len(body)), 'Cache-Control': 'no-store',
                     'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                     'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                     **(extra or {})}.items(): self.send_header(k, v)
        self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError): pass

    def host_ok(self):
        if self.headers.get('Host') != self.server.allowed_host:
            self.reply({'error': '仅支持从本机 127.0.0.1 地址访问'}, 403)
            return False
        return True

    def operation(self, method, data=None, extra=None):
        try:
            result = self.server.service.call(method, data)
            if method == 'bootstrap': result['token'] = self.server.token
            self.reply(result, extra=extra)
        except (BusyError, ConflictError) as e: self.reply({'error': str(e)}, 409)
        except (ValueError, TypeError, KeyError) as e: self.reply({'error': str(e)}, 400)
        except Exception as e:
            print(f'API error: {type(e).__name__}: {e}', file=sys.stderr)
            self.reply({'error': '保存或运行失败，请检查本地服务日志'}, 500)

    def do_GET(self):
        if not self.host_ok(): return
        parsed = urllib.parse.urlparse(self.path)
        path, params = parsed.path, urllib.parse.parse_qs(parsed.query)
        if path == '/api/solution': return self.reply({'error': '请通过界面展开参考答案'}, 405)
        if path in ('/api/bootstrap', '/api/state', '/api/draft', '/api/history', '/api/export'):
            return self.operation(path.rsplit('/', 1)[1], dict(id=params.get('id', [''])[0], language=params.get('language', ['python'])[0]),
                                  {'Content-Disposition': 'attachment; filename="seagull-backup.json"'} if path == '/api/export' else None)
        files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
        if path not in files: return self.reply({'error': '页面不存在'}, 404)
        filename, kind = files[path]
        self.reply((ROOT / 'static' / filename).read_bytes(), kind=kind + '; charset=utf-8')

    def do_POST(self):
        if not self.host_ok(): return
        if self.headers.get('X-Seagull-Token') != self.server.token or self.headers.get('Origin', self.server.origin) != self.server.origin:
            return self.reply({'error': '请求来源或会话校验失败，请刷新本机页面'}, 403)
        methods = {'/api/draft': 'saveDraft', '/api/judge': 'judge', '/api/progress': 'progress',
                   '/api/solution': 'solution', '/api/knowledge': 'knowledge', '/api/import': 'import'}
        method = methods.get(urllib.parse.urlparse(self.path).path)
        if not method: return self.reply({'error': '接口不存在'}, 404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 20_000_000: raise ValueError('请求为空或超过 20 MB')
            if 'application/json' not in self.headers.get('Content-Type', ''): raise ValueError('仅支持 JSON 请求')
            data = json.loads(self.rfile.read(length))
        except (ValueError, TypeError) as e: return self.reply({'error': str(e)}, 400)
        self.operation(method, data)

def main():
    parser = argparse.ArgumentParser(description='Seagull 本地 Python/Rust 练习台')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('SEAGULL_DATA_DIR', str(ROOT / 'data'))))
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    try: server = AppServer(('127.0.0.1', args.port), args.data_dir)
    except OSError as e:
        print(f'启动失败：{e}\n端口占用时可运行 python server.py --port 8766', file=sys.stderr)
        return 1
    print(f'Seagull 练习台：{server.origin}\n数据目录：{server.store.folder.resolve()}\n仅运行你自己信任的代码。按 Ctrl+C 停止。', flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(server.origin)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0

if __name__ == '__main__': raise SystemExit(main())
