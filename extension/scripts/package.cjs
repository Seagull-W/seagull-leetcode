const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const manifest = require('../package.json');
const output = path.resolve(root, '../work/dist', `${manifest.name}-${manifest.version}.vsix`);
const args = ['package', '--no-dependencies', '-o', output];
// CI artifacts may be built before the owner chooses a license. Releases cannot.
if (!fs.existsSync(path.join(root, 'LICENSE'))) {
  if (process.env.SEAGULL_RELEASE === 'true') throw new Error('Choose a LICENSE before publishing.');
  console.warn('No LICENSE selected: development VSIX only; release:check will reject publication.');
  args.push('--skip-license');
}
const result = spawnSync(process.execPath, [require.resolve('@vscode/vsce/vsce'), ...args], {cwd:root,stdio:'inherit'});
if (result.error) throw result.error;
process.exit(result.status ?? 1);
