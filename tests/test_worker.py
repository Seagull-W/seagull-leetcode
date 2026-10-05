"""Exercise shared service and the real asynchronous stdio worker."""
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from content.catalog import BY_ID
from service import Service
from store import Store, ConflictError

ROOT = Path(__file__).resolve().parents[1]

class ServiceTests(unittest.TestCase):
    def test_revision_conflict_and_old_database_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            old = Store(Path(folder)/'old')
            old.save_draft('a01','python','old draft')
            old.add_submission('a01','python','snapshot','submit',1,{'status':'通过'})
            original = old.export()['tables']
            service = Service(Path(folder)/'new')
            result = service.call('importDatabase',{'path':str(old.path)})
            self.assertEqual(result['imported'],2)
            self.assertEqual(old.export()['tables'],original)
            draft = service.call('draft',{'id':'a01'})['draft']
            saved = service.call('saveDraft',{'id':'a01','code':'one','expected':draft['updated_at']})
            with self.assertRaises(ConflictError):
                service.call('saveDraft',{'id':'a01','code':'stale','expected':draft['updated_at']})
            self.assertEqual(service.call('draft',{'id':'a01'})['draft']['code'],'one')
            self.assertNotEqual(saved['saved_at'],draft['updated_at'])
    def test_new_draft_conflict_and_schema_compatibility(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            first = store.save_draft('a01','rust','one',expected=None)
            with self.assertRaises(ConflictError):store.save_draft('a01','rust','two',expected=None)
            second = store.save_draft('a01','rust','two',expected=first)
            self.assertNotEqual(first,second)
            self.assertEqual(store.export()['version'],1)

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.proc = subprocess.Popen([sys.executable,'-u','-X','utf8',str(ROOT/'worker.py'),'--data-dir',self.temp.name],
                                     stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.responses = queue.Queue()
        self.reader = threading.Thread(target=self.read,daemon=True);self.reader.start()
    def read(self):
        for line in self.proc.stdout:self.responses.put(json.loads(line))
    def send(self,rid,method,params=None,version=1):
        self.proc.stdin.write((json.dumps(dict(id=rid,method=method,params=params or {},version=version))+'\n').encode('utf-8'));self.proc.stdin.flush()
    def response(self):return self.responses.get(timeout=10)
    def tearDown(self):
        if not self.proc.stdin.closed:self.proc.stdin.close()
        self.proc.wait(timeout=10);self.reader.join(timeout=2)
        self.proc.stdout.close();self.proc.stderr.close();self.temp.cleanup()
    def test_bootstrap_and_protocol_validation(self):
        self.send('1','bootstrap');r=self.response();self.assertEqual(r['version'],1);self.assertEqual(len(r['result']['problems']),63)
        self.assertNotIn('solutions',r['result']['problems'][0])
        self.send('2','state',version=99);self.assertEqual(self.response()['error']['code'],'invalid')
        self.send('3','unknown');self.assertEqual(self.response()['error']['code'],'invalid')
        self.proc.stdin.write(b'[]\n');self.proc.stdin.flush();self.assertEqual(self.response()['error']['code'],'invalid')
    def test_save_read_snapshot_and_restart(self):
        code=BY_ID['a01']['solutions']['python']
        self.send('1','saveDraft',{'id':'a01','code':code,'expected':None});self.assertIn('saved_at',self.response()['result'])
        self.send('2','judge',{'id':'a01','code':code,'mode':'submit'});r=self.response();self.assertEqual(r['result']['result']['status'],'通过')
        self.send('3','history',{'id':'a01'});self.assertEqual(self.response()['result']['history'][0]['code'],code)
        self.assertEqual(Store(self.temp.name).state()['statuses']['a01:python'],'已通过')
    def test_cancel_keeps_worker_responsive_and_cleans_runs(self):
        self.send('judge','judge',{'id':'a01','code':'def solve(nums):\n    while True: pass','mode':'submit'})
        time.sleep(.25)
        self.send('state','state');self.assertEqual(self.response()['id'],'state')
        self.send('cancel','cancel',{'request_id':'judge'})
        answers=[self.response(),self.response()]
        by_id={a['id']:a for a in answers}
        self.assertTrue(by_id['cancel']['result']['cancelled'])
        self.assertEqual(by_id['judge']['result']['result']['status'],'已取消')
        self.assertFalse(list((Path(self.temp.name)/'runs').iterdir()))
    def test_eof_cancels_active_process(self):
        self.send('judge','judge',{'id':'a01','code':'def solve(nums):\n    while True: pass'})
        time.sleep(.2);started=time.monotonic();self.proc.stdin.close()
        self.proc.wait(timeout=5);self.assertLess(time.monotonic()-started,3)

if __name__=='__main__':unittest.main()
