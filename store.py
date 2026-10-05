"""Versioned SQLite records, transactional merge imports, and safe backups."""
from contextlib import contextmanager
import datetime as dt
import json
from pathlib import Path
import sqlite3
import uuid

class ConflictError(ValueError): pass
_UNSET = object()

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')

class Store:
    def __init__(self, folder):
        self.folder=Path(folder); self.folder.mkdir(parents=True,exist_ok=True)
        self.path=self.folder/'practice.sqlite3'
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            INSERT OR IGNORE INTO meta VALUES ('schema_version','1');
            CREATE TABLE IF NOT EXISTS drafts(problem_id TEXT,language TEXT,code TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(problem_id,language));
            CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY,problem_id TEXT NOT NULL,language TEXT NOT NULL,code TEXT NOT NULL,mode TEXT NOT NULL,problem_version INTEGER NOT NULL,result TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS submission_problem ON submissions(problem_id,language,created_at);
            CREATE TABLE IF NOT EXISTS progress(problem_id TEXT PRIMARY KEY,bookmark INTEGER NOT NULL DEFAULT 0,mastery TEXT NOT NULL DEFAULT '未自评',notes TEXT NOT NULL DEFAULT '',review_at TEXT,seen_answer INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS knowledge(id TEXT PRIMARY KEY,answer TEXT NOT NULL,mastery TEXT NOT NULL DEFAULT '未自评',updated_at TEXT NOT NULL);
            ''')
            version=db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            if version!='1': raise ValueError('数据库版本不受支持；请使用对应版本程序。')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15);db.row_factory=sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback();raise
        finally: db.close()

    def state(self):
        with self.connect() as db:
            progress={r['problem_id']:dict(r) for r in db.execute('SELECT * FROM progress')}
            statuses={}
            for r in db.execute('SELECT problem_id,language,mode,result FROM submissions ORDER BY created_at ASC'):
                if r['mode']!='submit': continue
                key=r['problem_id']+':'+r['language']
                passed=json.loads(r['result']).get('status')=='通过'
                statuses[key]='已通过' if passed or statuses.get(key)=='已通过' else '尝试中'
            return dict(progress=progress,statuses=statuses,knowledge={r['id']:dict(r) for r in db.execute('SELECT * FROM knowledge')})

    def draft(self,pid,lang):
        with self.connect() as db:
            r=db.execute('SELECT * FROM drafts WHERE problem_id=? AND language=?',(pid,lang)).fetchone()
            return dict(r) if r else None

    def save_draft(self,pid,lang,code,expected=_UNSET):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT updated_at FROM drafts WHERE problem_id=? AND language=?',(pid,lang)).fetchone()
            current=row['updated_at'] if row else None
            if expected is not _UNSET and expected!=current:
                raise ConflictError('草稿已被其他窗口更新；请比较版本后再保存')
            moment=dt.datetime.now(dt.timezone.utc)
            if current and moment<=dt.datetime.fromisoformat(current):
                moment=dt.datetime.fromisoformat(current)+dt.timedelta(microseconds=1)
            stamp=moment.isoformat(timespec='microseconds')
            db.execute('INSERT INTO drafts VALUES(?,?,?,?) ON CONFLICT(problem_id,language) DO UPDATE SET code=excluded.code,updated_at=excluded.updated_at',(pid,lang,code,stamp))
        return stamp

    def add_submission(self,pid,lang,code,mode,version,result):
        record=dict(id=str(uuid.uuid4()),problem_id=pid,language=lang,code=code,mode=mode,problem_version=version,result=json.dumps(result,ensure_ascii=False),created_at=now())
        with self.connect() as db:
            db.execute('INSERT INTO submissions VALUES(:id,:problem_id,:language,:code,:mode,:problem_version,:result,:created_at)',record)
        return record['id']

    def history(self,pid,lang):
        with self.connect() as db:
            rows=[dict(r) for r in db.execute('SELECT * FROM submissions WHERE problem_id=? AND language=? ORDER BY created_at DESC LIMIT 100',(pid,lang))]
        for r in rows:r['result']=json.loads(r['result'])
        return rows

    def update_progress(self,pid,changes):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO progress(problem_id,updated_at) VALUES(?,?)',(pid,now()))
            allowed={'bookmark','mastery','notes','review_at','seen_answer'}
            for key,value in changes.items():
                if key not in allowed: continue
                if key=='seen_answer':
                    db.execute('UPDATE progress SET seen_answer=MAX(seen_answer,?) WHERE problem_id=?',(int(value),pid))
                else: db.execute(f'UPDATE progress SET {key}=? WHERE problem_id=?',(value,pid))
            db.execute('UPDATE progress SET updated_at=? WHERE problem_id=?',(now(),pid))

    def save_knowledge(self,kid,answer,mastery):
        with self.connect() as db:
            db.execute('INSERT INTO knowledge VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET answer=excluded.answer,mastery=excluded.mastery,updated_at=excluded.updated_at',(kid,answer,mastery,now()))

    def export(self):
        with self.connect() as db:
            db.execute('BEGIN')
            return dict(format='seagull-practice',version=1,exported_at=now(),tables={name:[dict(r) for r in db.execute(f'SELECT * FROM {name}')] for name in ('drafts','submissions','progress','knowledge')})

    def import_data(self,payload,problem_ids,knowledge_ids):
        if not isinstance(payload,dict) or payload.get('format')!='seagull-practice' or payload.get('version')!=1:
            raise ValueError('不是受支持的 Seagull 备份文件')
        schemas={
            'drafts':{'problem_id':str,'language':str,'code':str,'updated_at':str},
            'submissions':{'id':str,'problem_id':str,'language':str,'code':str,'mode':str,'problem_version':int,'result':str,'created_at':str},
            'progress':{'problem_id':str,'bookmark':int,'mastery':str,'notes':str,'review_at':(str,type(None)),'seen_answer':int,'updated_at':str},
            'knowledge':{'id':str,'answer':str,'mastery':str,'updated_at':str}}
        tables=payload.get('tables')
        if not isinstance(tables,dict) or set(tables)!=set(schemas): raise ValueError('备份表结构错误')
        for name,schema in schemas.items():
            rows=tables[name]
            if not isinstance(rows,list) or len(rows)>100000: raise ValueError('备份记录数量错误')
            for row in rows:
                if not isinstance(row,dict) or set(row)!=set(schema):raise ValueError('备份字段错误')
                if any(not isinstance(row[k],t) for k,t in schema.items()):raise ValueError('备份字段类型错误')
                if 'problem_id' in row and row['problem_id'] not in problem_ids:raise ValueError('备份包含未知题目')
                if name=='knowledge' and row['id'] not in knowledge_ids:raise ValueError('备份包含未知知识题')
                if 'language' in row and row['language'] not in ('python','rust'):raise ValueError('备份语言错误')
                stamp=row.get('updated_at',row.get('created_at'))
                try:
                    parsed=dt.datetime.fromisoformat(stamp)
                    if parsed.tzinfo is None:raise ValueError()
                except (TypeError,ValueError):raise ValueError('备份时间格式错误') from None
                if len(row.get('code','').encode('utf-8'))>100000:raise ValueError('备份代码过长')
                if name=='submissions':
                    try:result=json.loads(row['result'])
                    except ValueError:raise ValueError('备份判题结果错误') from None
                    if not isinstance(result,dict) or not isinstance(result.get('status'),str):raise ValueError('备份判题结果错误')
                    if row['mode'] not in ('run','submit'):raise ValueError('备份运行方式错误')
                if name=='progress':
                    if row['bookmark'] not in (0,1) or row['seen_answer'] not in (0,1):raise ValueError('备份标记错误')
                    if row['review_at']:
                        try:dt.date.fromisoformat(row['review_at'])
                        except ValueError:raise ValueError('备份复习日期错误') from None
        # Validate fully before changing anything. Keep a rollback backup on disk.
        backup=self.folder/('before-import-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]+'.json')
        backup.write_text(json.dumps(self.export(),ensure_ascii=False,indent=2),encoding='utf-8')
        count=0
        with self.connect() as db:
            for name,schema in schemas.items():
                cols=list(schema);keys=['problem_id','language'] if name=='drafts' else ['problem_id'] if name=='progress' else ['id']
                for row in tables[name]:
                    where=' AND '.join(k+'=?' for k in keys)
                    existing=db.execute(f'SELECT * FROM {name} WHERE {where}',[row[k] for k in keys]).fetchone()
                    if existing:
                        if name=='submissions':continue
                        if dt.datetime.fromisoformat(existing['updated_at'])>=dt.datetime.fromisoformat(row['updated_at']):continue
                        # Viewing a solution is a historical fact; preserve it on merge.
                        if name=='progress':row={**row,'seen_answer':max(row['seen_answer'],existing['seen_answer'])}
                        assignments=','.join(k+'=?' for k in cols if k not in keys)
                        db.execute(f'UPDATE {name} SET {assignments} WHERE {where}',[row[k] for k in cols if k not in keys]+[row[k] for k in keys])
                    else:
                        db.execute(f'INSERT INTO {name} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})',[row[k] for k in cols])
                    count+=1
        return dict(imported=count,backup=backup.name)
