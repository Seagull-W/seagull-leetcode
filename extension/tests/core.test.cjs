const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {CoreBridge} = require('../out/core');
const testRoot = path.resolve(__dirname,'../../work/node-tests');
test('actual Python worker transport supports spaces, revisions, cancellation and restart', async () => {
  await fs.mkdir(testRoot,{recursive:true});
  const dataDir=await fs.mkdtemp(path.join(testRoot,'transport with spaces '));
  const options={python:process.env.SEAGULL_TEST_PYTHON || 'python',script:path.resolve(__dirname,'../python/worker.py'),dataDir};
  let core=new CoreBridge(options);
  try {
    const bootstrap=await core.request('bootstrap');assert.equal(bootstrap.problems.length,63);
    const first=await core.request('saveDraft',{id:'a01',code:'version one',expected:null});
    await assert.rejects(core.request('saveDraft',{id:'a01',code:'stale',expected:null}),e=>e.code==='conflict');
    assert.equal((await core.request('draft',{id:'a01'})).draft.code,'version one');
    let rid;const running=core.request('judge',{id:'a01',code:'def solve(nums):\n    while True: pass'},45000,id=>{rid=id;});
    await new Promise(resolve=>setTimeout(resolve,250));
    const state=await core.request('state');assert.ok(state.statuses);
    const cancelled=await core.request('cancel',{request_id:rid});assert.equal(cancelled.cancelled,true);
    assert.equal((await running).result.status,'已取消');
    const second=await core.request('saveDraft',{id:'a01',code:'version two',expected:first.saved_at});assert.notEqual(second.saved_at,first.saved_at);
    core.dispose();
    core=new CoreBridge(options);
    assert.equal((await core.request('draft',{id:'a01'})).draft.code,'version two');
    assert.ok((await fs.stat(path.join(dataDir,'tmp'))).isDirectory());
  } finally {core.dispose();}
});
test('missing Python reports a configuration error and does not hang', async () => {
  const core=new CoreBridge({python:path.join(testRoot,'does-not-exist'),script:'worker.py',dataDir:testRoot});
  try {await assert.rejects(core.request('bootstrap'),/Python|ENOENT/);} finally {core.dispose();}
});
