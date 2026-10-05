"""Run: python -X utf8 -m unittest discover -s tests -v"""
import copy
import datetime as dt
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from content.catalog import BY_ID,PROBLEMS
from content.lessons import KNOWLEDGE,LESSONS
from judge import equal,judge
from server import AppServer
from store import Store

class JudgeTests(unittest.TestCase):
    def test_exact_types_and_multisets(self):
        self.assertFalse(equal(True,1));self.assertFalse(equal([True],[1]))
        self.assertTrue(equal([[2],[1]],[[1],[2]],True))
        self.assertFalse(equal([[1],[1]],[[1]],True))
    def test_wrong_output(self):
        result=judge(BY_ID['a01'],'python','def solve(nums): return nums')
        self.assertEqual(result['status'],'答案错误');self.assertLess(result['passed'],result['total'])
    def test_python_runtime_error(self):
        result=judge(BY_ID['a01'],'python','def solve(nums): raise ValueError("test")')
        self.assertEqual(result['status'],'运行错误');self.assertIn('ValueError',result['stderr'])
    def test_python_timeout(self):
        result=judge(BY_ID['a01'],'python','def solve(nums):\n    while True: pass')
        self.assertEqual(result['status'],'超时')
    def test_output_limit(self):
        result=judge(BY_ID['a01'],'python','def solve(nums):\n    while True: print("x"*10000,flush=True)')
        self.assertEqual(result['status'],'输出过多')
    @unittest.skipUnless(shutil.which('rustc'),'Rust not installed')
    def test_rust_compile_error(self):
        result=judge(BY_ID['a01'],'rust','pub fn solve(nums: Vec<i64>) -> Vec<i64> { definitely_invalid }')
        self.assertEqual(result['status'],'编译错误');self.assertIn('error',result['stderr'])

class StoreTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def seed(self):
        s=self.store;s.save_draft('a01','python','my python');s.save_draft('a01','rust','my rust')
        s.update_progress('a01',{'mastery':'独立完成','notes':'中文笔记','bookmark':1,'review_at':'2026-10-06'})
        s.save_knowledge('k01','我的回答','提示后完成')
        s.add_submission('a01','python','snapshot','submit',1,{'status':'通过','passed':1,'total':1,'message':'ok'})
    def test_restart_and_language_isolation(self):
        self.seed();s=Store(self.temp.name)
        self.assertEqual(s.draft('a01','python')['code'],'my python');self.assertEqual(s.draft('a01','rust')['code'],'my rust')
        self.assertEqual(s.state()['statuses']['a01:python'],'已通过')
        self.assertNotIn('a01:rust',s.state()['statuses'])
        self.assertEqual(s.state()['knowledge']['k01']['answer'],'我的回答')
    def test_export_import_and_duplicate_merge(self):
        self.seed();payload=self.store.export()
        with tempfile.TemporaryDirectory() as folder:
            s=Store(folder);r=s.import_data(payload,set(BY_ID),{k['id'] for k in KNOWLEDGE});self.assertEqual(r['imported'],5)
            self.assertTrue((Path(folder)/r['backup']).exists())
            self.assertEqual(s.history('a01','python')[0]['code'],'snapshot')
            self.assertEqual(s.import_data(payload,set(BY_ID),{k['id'] for k in KNOWLEDGE})['imported'],0)
            # Older backups cannot overwrite a newer local draft.
            s.save_draft('a01','python','newer');s.import_data(payload,set(BY_ID),{k['id'] for k in KNOWLEDGE})
            self.assertEqual(s.draft('a01','python')['code'],'newer')
    def test_invalid_import_leaves_database_unchanged(self):
        self.seed();before=self.store.export()['tables'];bad=self.store.export();bad['tables']['drafts'][0]['language']='sh'
        with self.assertRaises(ValueError):self.store.import_data(bad,set(BY_ID),{k['id'] for k in KNOWLEDGE})
        self.assertEqual(self.store.export()['tables'],before)
    def test_run_does_not_mark_passed(self):
        self.store.add_submission('a01','python','x','run',1,{'status':'通过'})
        self.assertNotIn('a01:python',self.store.state()['statuses'])
    def test_answer_seen_is_monotonic(self):
        self.store.update_progress('a01',{'seen_answer':1});self.store.update_progress('a01',{'seen_answer':0})
        self.assertEqual(self.store.state()['progress']['a01']['seen_answer'],1)

class APITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.server=AppServer(('127.0.0.1',0),self.temp.name)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=self.server.origin
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,data=None,token=None,origin=None,host=None):
        headers={};body=None
        if data is not None:
            body=json.dumps(data).encode();headers={'Content-Type':'application/json','X-Seagull-Token':self.server.token if token is None else token}
        if origin:headers['Origin']=origin
        if host:headers['Host']=host
        req=urllib.request.Request(self.url+path,data=body,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=35) as res:return res.status,json.loads(res.read())
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
    def test_catalog_and_solution_visibility(self):
        status,data=self.request('/api/bootstrap');self.assertEqual(status,200)
        self.assertEqual(len(data['problems']),63);self.assertEqual(len(data['knowledge']),10)
        self.assertNotIn('solutions',data['problems'][0]);self.assertNotIn('cases',data['problems'][0])
    def test_reject_cross_origin_and_invalid_token(self):
        data={'id':'a01','language':'python','code':'def solve(nums): return []'}
        self.assertEqual(self.request('/api/draft',data,token='wrong')[0],403)
        self.assertEqual(self.request('/api/draft',data,origin='https://other.example')[0],403)
        self.assertEqual(self.request('/api/bootstrap',host='evil.example')[0],403)
    def test_submit_history_draft_restore(self):
        p=BY_ID['a01'];data={'id':p['id'],'language':'python','code':p['solutions']['python']}
        self.assertEqual(self.request('/api/draft',data)[0],200)
        status,result=self.request('/api/judge',data|{'mode':'submit'});self.assertEqual(status,200);self.assertEqual(result['result']['status'],'通过')
        _,history=self.request('/api/history?id=a01&language=python');self.assertEqual(history['history'][0]['code'],data['code'])
        # Later edits remain draft; resubmitting an old snapshot cannot overwrite them.
        self.request('/api/draft',data|{'code':'new draft'})
        self.request('/api/judge',data|{'mode':'run'})
        _,draft=self.request('/api/draft?id=a01&language=python');self.assertEqual(draft['draft']['code'],'new draft')
        self.assertEqual(len(self.server.store.history('a01','python')),2)
    def test_mark_solution_seen(self):
        _,data=self.request('/api/solution',{'id':'a01','language':'rust'})
        self.assertIn('pub fn solve',data['code']);self.assertEqual(self.server.store.state()['progress']['a01']['seen_answer'],1)
    def test_invalid_mode_and_large_code(self):
        self.assertEqual(self.request('/api/judge',{'id':'a01','language':'python','code':'x','mode':'shell'})[0],400)
        self.assertEqual(self.request('/api/draft',{'id':'a01','code':'x'*100001})[0],400)

if __name__=='__main__':unittest.main()
