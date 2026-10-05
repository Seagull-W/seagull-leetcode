"""Shared application operations for HTTP and the VS Code stdio worker."""
import datetime as dt
import shutil
import sqlite3
import sys
import threading
import json
from pathlib import Path
from content.catalog import PROBLEMS, BY_ID
from content.lessons import LESSONS, KNOWLEDGE
from judge import judge
from store import Store

MASTERY = ('未自评', '独立完成', '提示后完成', '看解答后完成', '需要重做')

class BusyError(ValueError): pass

def problem_public(p):
    return {k: v for k, v in p.items() if k not in ('cases', 'solutions')} | {
        'examples': p['cases'][:2], 'test_count': len(p['cases'])}

def text(value, limit):
    if not isinstance(value, str) or len(value.encode('utf-8')) > limit:
        raise ValueError('文本类型或长度不合法')
    return value

class Service:
    def __init__(self, data_dir, rustc=None):
        self.store = Store(data_dir)
        self.rustc = rustc
        self.judge_lock = threading.BoundedSemaphore(1)

    def call(self, method, data=None, cancel=None):
        data = {} if data is None else data
        if not isinstance(data, dict): raise ValueError('请求结构错误')
        s = self.store
        if method == 'bootstrap':
            return dict(problems=[problem_public(p) for p in PROBLEMS], lessons=LESSONS,
                        knowledge=KNOWLEDGE, mastery=list(MASTERY), state=s.state(),
                        environment=dict(python=sys.version.split()[0], rust=bool(self.rustc or shutil.which('rustc')),
                                         data_dir=str(s.folder.resolve()), protocol=1))
        if method == 'state': return s.state()
        if method == 'export': return s.export()
        if method == 'import': return s.import_data(data, set(BY_ID), {k['id'] for k in KNOWLEDGE})
        if method == 'importDatabase':
            source = Path(text(data.get('path'), 10000)).resolve(strict=True)
            if source == s.path.resolve(): raise ValueError('当前数据库无需再次迁移')
            if source.suffix != '.sqlite3' or source.stat().st_size > 20_000_000: raise ValueError('请选择不超过 20 MB 的旧版 SQLite 数据库')
            # Read a consistent snapshot, including WAL; never initialize or update the source schema.
            db = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
            db.row_factory = sqlite3.Row
            try:
                db.execute('BEGIN')
                version = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
                if not version or version[0] != '1': raise ValueError('旧数据库版本不受支持')
                payload = dict(format='seagull-practice', version=1, tables={
                    name: [dict(row) for row in db.execute(f'SELECT * FROM {name}')]
                    for name in ('drafts', 'submissions', 'progress', 'knowledge')})
            finally: db.close()
            if len(json.dumps(payload).encode('utf-8')) > 20_000_000: raise ValueError('旧数据库记录超过 20 MB，请先分批导出')
            return s.import_data(payload, set(BY_ID), {k['id'] for k in KNOWLEDGE})
        if method == 'knowledge':
            kid = data.get('id')
            if kid not in {k['id'] for k in KNOWLEDGE}: raise ValueError('知识题不存在')
            mastery = data.get('mastery', '未自评')
            if mastery not in MASTERY: raise ValueError('掌握程度不合法')
            s.save_knowledge(kid, text(data.get('answer'), 20000), mastery)
            return dict(saved=True)
        if method not in ('draft', 'saveDraft', 'history', 'judge', 'progress', 'solution'):
            raise ValueError('操作不存在')
        pid, lang = data.get('id', ''), data.get('language', 'python')
        if pid not in BY_ID: raise ValueError('题目不存在')
        if lang not in ('python', 'rust'): raise ValueError('语言不支持')
        if method == 'draft': return dict(draft=s.draft(pid, lang))
        if method == 'history': return dict(history=s.history(pid, lang))
        if method == 'saveDraft':
            options = {'expected': data['expected']} if 'expected' in data else {}
            return dict(saved_at=s.save_draft(pid, lang, text(data.get('code'), 100000), **options))
        if method == 'solution':
            s.update_progress(pid, {'seen_answer': 1})
            return dict(code=BY_ID[pid]['solutions'][lang])
        if method == 'progress':
            changes = data.get('changes')
            if not isinstance(changes, dict): raise ValueError('进度格式错误')
            for k, v in changes.items():
                if k not in ('bookmark', 'seen_answer', 'mastery', 'notes', 'review_at'): raise ValueError('进度字段不支持')
                if k in ('bookmark', 'seen_answer') and (type(v) != int or v not in (0, 1)): raise ValueError('标记不合法')
                if k == 'mastery' and v not in MASTERY: raise ValueError('掌握程度不合法')
                if k == 'notes': text(v, 20000)
                if k == 'review_at' and v is not None: dt.date.fromisoformat(v)
            s.update_progress(pid, changes)
            return s.state()
        code = text(data.get('code'), 100000)
        mode = data.get('mode', 'submit')
        if mode not in ('run', 'submit'): raise ValueError('运行模式错误')
        if not self.judge_lock.acquire(blocking=False): raise BusyError('已有代码正在运行，请等待当前判题完成')
        try:
            result = judge(BY_ID[pid], lang, code, mode, s.folder / 'runs', cancel=cancel, rustc=self.rustc)
            sid = s.add_submission(pid, lang, code, mode, BY_ID[pid]['version'], result)
        finally:
            self.judge_lock.release()
        return dict(result=result, submission_id=sid, state=s.state())
