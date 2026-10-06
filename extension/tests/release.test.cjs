const test=require('node:test');
const assert=require('node:assert/strict');
const {validate}=require('../scripts/release-check.cjs');
const manifest=require('../package.json');
test('publication accepts matching release metadata',()=>{
  assert.equal(validate(`v${manifest.version}`).version,manifest.version);
});
test('publication rejects mismatched and unsafe tags',()=>{
  for(const tag of ['v99.99.99','main','v0.2.1\nmalicious','v0.2.1-beta.1','']) {
    assert.throws(()=>validate(tag),/tag|Tag/);
  }
});
