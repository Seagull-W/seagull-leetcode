"""Dependency-free, loopback-only personal coding practice server."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

from content.catalog import PROBLEMS,BY_ID
from content.lessons import LESSONS,KNOWLEDGE
from judge import judge
from store import Store

ROOT=Path(__file__).resolve().parent
MASTERY=('未自评','独立完成','提示后完成','看解答后完成','需要重做')

def problem_public(p):
    return {k:v for k,v in p.items() if k not in ('cases','solutions')} | {'examples':p['cases'][:2],'test_count':len(p['cases'])}

class AppServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,data_dir):
        super().__init__(address,Handler)
        self.store=Store(data_dir);self.token=secrets.token_urlsafe(32)
        self.judge_lock=threading.BoundedSemaphore(1)
        self.allowed_host=f'127.0.0.1:{self.server_address[1]}'
        self.origin='http://'+self.allowed_host

class Handler(BaseHTTPRequestHandler):
    server_version='Seagull/1.0'
    def log_message(self,fmt,*args):
        # Do not log user code, URLs containing text, or request bodies.
        pass

    def reply(self,payload,status=200,kind='application/json; charset=utf-8',extra=None):
        body=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key,value in (extra or {}).items():self.send_header(key,value)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass

    def host_ok(self):
        if self.headers.get('Host')!=self.server.allowed_host:
            self.reply({'error':'仅支持从本机 127.0.0.1 地址访问'},403);return False
        return True

    def do_GET(self):
        if not self.host_ok():return
        parsed=urllib.parse.urlparse(self.path);path=parsed.path
        params=urllib.parse.parse_qs(parsed.query)
        try:
            if path=='/api/bootstrap':
                return self.reply(dict(token=self.server.token,problems=[problem_public(p) for p in PROBLEMS],lessons=LESSONS,
                    knowledge=KNOWLEDGE,mastery=list(MASTERY),environment=dict(python=sys.version.split()[0],rust=bool(shutil.which('rustc'))),state=self.server.store.state()))
            if path=='/api/state':return self.reply(self.server.store.state())
            if path in ('/api/draft','/api/history','/api/solution'):
                pid=params.get('id',[''])[0];lang=params.get('language',['python'])[0]
                self.validate_problem(pid,lang)
                if path=='/api/draft':return self.reply(dict(draft=self.server.store.draft(pid,lang)))
                if path=='/api/history':return self.reply(dict(history=self.server.store.history(pid,lang)))
                # Solution is read through POST so viewing it updates a durable historical flag.
                return self.reply({'error':'请通过界面展开参考答案'},405)
            if path=='/api/export':
                return self.reply(self.server.store.export(),extra={'Content-Disposition':'attachment; filename="seagull-backup.json"'})
            files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if path in files:
                kind={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[path]
                return self.reply((ROOT/'static'/files[path]).read_bytes(),kind=kind)
            self.reply({'error':'页面不存在'},404)
        except (ValueError,KeyError) as e:self.reply({'error':str(e)},400)
        except Exception:self.reply({'error':'读取失败，请检查本地数据目录和服务日志'},500)

    def validate_problem(self,pid,lang):
        if pid not in BY_ID:raise ValueError('题目不存在')
        if lang not in ('python','rust'):raise ValueError('语言不支持')

    def text(self,value,limit):
        if not isinstance(value,str) or len(value.encode('utf-8'))>limit:raise ValueError('文本类型或长度不合法')
        return value

    def do_POST(self):
        if not self.host_ok():return
        if self.headers.get('X-Seagull-Token')!=self.server.token or self.headers.get('Origin',self.server.origin)!=self.server.origin:
            return self.reply({'error':'请求来源或会话校验失败，请刷新本机页面'},403)
        path=urllib.parse.urlparse(self.path).path
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=20_000_000:raise ValueError('请求为空或超过 20 MB')
            if 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('仅支持 JSON 请求')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('请求结构错误')
            store=self.server.store
            if path in ('/api/draft','/api/judge','/api/progress','/api/solution'):
                pid=data.get('id','');lang=data.get('language','python');self.validate_problem(pid,lang)
            if path=='/api/draft':
                stamp=store.save_draft(pid,lang,self.text(data.get('code'),100000));return self.reply(dict(saved_at=stamp))
            if path=='/api/judge':
                code=self.text(data.get('code'),100000);mode=data.get('mode','submit')
                if mode not in ('run','submit'):raise ValueError('运行模式错误')
                if not self.server.judge_lock.acquire(blocking=False):return self.reply({'error':'已有代码正在运行，请等待当前判题完成'},409)
                try:
                    result=judge(BY_ID[pid],lang,code,mode,store.folder/'runs')
                    sid=store.add_submission(pid,lang,code,mode,BY_ID[pid]['version'],result)
                finally:self.server.judge_lock.release()
                return self.reply(dict(result=result,submission_id=sid,state=store.state()))
            if path=='/api/progress':
                changes=data.get('changes')
                if not isinstance(changes,dict):raise ValueError('进度格式错误')
                for k,v in changes.items():
                    if k in ('bookmark','seen_answer') and (type(v)!=int or v not in (0,1)):raise ValueError('标记不合法')
                    if k=='mastery' and v not in MASTERY:raise ValueError('掌握程度不合法')
                    if k=='notes':self.text(v,20000)
                    if k=='review_at' and v is not None:dt.date.fromisoformat(v)
                store.update_progress(pid,changes);return self.reply(store.state())
            if path=='/api/solution':
                store.update_progress(pid,{'seen_answer':1});return self.reply(dict(code=BY_ID[pid]['solutions'][lang]))
            if path=='/api/knowledge':
                kid=data.get('id')
                if kid not in {k['id'] for k in KNOWLEDGE}:raise ValueError('知识题不存在')
                mastery=data.get('mastery','未自评')
                if mastery not in MASTERY:raise ValueError('掌握程度不合法')
                store.save_knowledge(kid,self.text(data.get('answer'),20000),mastery);return self.reply(dict(saved=True))
            if path=='/api/import':
                return self.reply(store.import_data(data,set(BY_ID),{k['id'] for k in KNOWLEDGE}))
            self.reply({'error':'接口不存在'},404)
        except (ValueError,TypeError,KeyError) as e:self.reply({'error':str(e)},400)
        except Exception as e:
            print(f'API error: {type(e).__name__}: {e}',file=sys.stderr)
            self.reply({'error':'保存或运行失败，请检查服务日志；当前代码仍保留在编辑器'},500)

def main():
    parser=argparse.ArgumentParser(description='Seagull 本地 Python/Rust 练习台')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--data-dir',type=Path,default=Path(os.environ.get('SEAGULL_DATA_DIR',str(ROOT/'data'))))
    parser.add_argument('--open',action='store_true',help='自动打开浏览器')
    args=parser.parse_args()
    try:server=AppServer(('127.0.0.1',args.port),args.data_dir)
    except OSError as e:
        print(f'启动失败：{e}\n端口占用时可运行 python server.py --port 8766',file=sys.stderr);return 1
    print(f'Seagull 练习台：{server.origin}\n数据目录：{server.store.folder.resolve()}\n题库：{len(PROBLEMS)} 道 Python/Rust 算法题、{len(KNOWLEDGE)} 道后训练知识题\n仅运行你自己信任的代码。按 Ctrl+C 停止。',flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(server.origin)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0

if __name__=='__main__':raise SystemExit(main())
