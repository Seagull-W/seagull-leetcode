const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const manifest = require('../package.json');
function validate(tag, options={}) {
  if (!/^v\d+\.\d+\.\d+$/.test(tag || '')) throw new Error('Release tag must be vMAJOR.MINOR.PATCH.');
  if (tag !== `v${manifest.version}`) throw new Error(`Tag ${tag} does not match version ${manifest.version}.`);
  const changelog=fs.readFileSync(path.join(root,'CHANGELOG.md'),'utf8');
  if (!changelog.includes(`## [${manifest.version}]`)) throw new Error('Missing CHANGELOG section for this version.');
  if (!fs.existsSync(path.join(root,'LICENSE')) || !manifest.license || manifest.license==='UNLICENSED') {
    throw new Error('Choose a license and set package.json license before a public release.');
  }
  if (!fs.existsSync(path.join(root,'extension',manifest.icon || ''))) throw new Error('Missing Marketplace icon.');
  if (options.checkGit) {
    const run=(args)=>{const r=spawnSync('git',args,{cwd:root,encoding:'utf8'});if(r.status!==0)throw new Error(r.stderr);return r.stdout.trim();};
    if (run(['rev-parse',`${tag}^{commit}`])!==run(['rev-parse','HEAD'])) throw new Error('Tag must point to the checked out commit.');
    run(['merge-base','--is-ancestor','HEAD','origin/main']);
  }
  return manifest;
}
module.exports={validate};
if (require.main===module) {
  try {
    const tag=process.argv[2] || process.env.RELEASE_TAG;
    validate(tag,{checkGit:process.argv.includes('--git')});
    console.log(`Release metadata OK: ${manifest.publisher}.${manifest.name} ${tag}`);
  } catch(error) {console.error(error.message);process.exitCode=1;}
}
