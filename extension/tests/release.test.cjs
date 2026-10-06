const test=require('node:test');
const assert=require('node:assert/strict');
const {validate}=require('../scripts/release-check.cjs');
const manifest=require('../package.json');
const {spawnSync}=require('node:child_process');
const path=require('node:path');
test('publication accepts matching release metadata',()=>{
  assert.equal(validate(`v${manifest.version}`).version,manifest.version);
});
test('git flag uses RELEASE_TAG rather than interpreting the flag as a tag',()=>{
  const result=spawnSync(process.execPath,[path.resolve(__dirname,'../scripts/release-check.cjs'),'--git'],{
    encoding:'utf8',env:{...process.env,RELEASE_TAG:'v99.99.99'}
  });
  assert.equal(result.status,1);
  assert.match(result.stderr,/Tag v99\.99\.99 does not match/);
});
test('publication rejects mismatched and unsafe tags',()=>{
  for(const tag of ['v99.99.99','main','v0.2.1\nmalicious','v0.2.1-beta.1','']) {
    assert.throws(()=>validate(tag),/tag|Tag/);
  }
});
