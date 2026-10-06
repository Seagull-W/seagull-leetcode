const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const compiled = spawnSync(process.execPath, [require.resolve('typescript/bin/tsc'), '-p', root], {stdio:'inherit'});
if (compiled.status) process.exit(compiled.status);
const source = path.resolve(root, '..'), bundle = path.join(root, 'python');
fs.mkdirSync(bundle, {recursive:true});
for (const file of ['worker.py','service.py','judge.py','store.py']) fs.copyFileSync(path.join(source,file),path.join(bundle,file));
fs.mkdirSync(path.join(bundle,'content'),{recursive:true});
for (const file of ['catalog.py','lessons.py','extra_cases.json']) fs.copyFileSync(path.join(source,'content',file),path.join(bundle,'content',file));
fs.copyFileSync(path.join(source,'docs','VSCODE.md'),path.join(root,'README.md'));
for (const file of ['CHANGELOG.md','LICENSE']) {
  const sourceFile=path.join(source,file), target=path.join(root,file);
  if (fs.existsSync(sourceFile)) fs.copyFileSync(sourceFile,target);
  else if (fs.existsSync(target)) fs.unlinkSync(target);
}
fs.mkdirSync(path.join(source,'work','dist'),{recursive:true});
