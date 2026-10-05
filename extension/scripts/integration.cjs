const path = require('node:path');
const fs = require('node:fs');
const {runTests} = require('@vscode/test-electron');
const root = path.resolve(__dirname,'..');
const testRoot = path.resolve(root,'../work/vscode-integration');
const workspace = path.join(testRoot,'workspace');
fs.mkdirSync(workspace,{recursive:true});
// Existing desktop installation avoids a large download. All test data remains on D: here.
const conventional = process.platform==='win32' ? path.join(process.env.LOCALAPPDATA || '', 'Programs','Microsoft VS Code','Code.exe') : undefined;
const executable = process.env.SEAGULL_VSCODE_EXECUTABLE || (conventional && fs.existsSync(conventional) ? conventional : undefined);
process.env.SEAGULL_INTEGRATION_DATA=path.join(testRoot,`data-${Date.now()}`);
runTests({
  vscodeExecutablePath:executable,
  extensionDevelopmentPath:root,
  extensionTestsPath:path.join(root,'out/test/integration.js'),
  launchArgs:[workspace,'--user-data-dir',path.join(testRoot,'user-data'),'--extensions-dir',path.join(testRoot,'extensions'),
    '--skip-welcome','--skip-release-notes','--disable-workspace-trust','--disable-extensions'],
  extensionTestsEnv:{SEAGULL_INTEGRATION_DATA:process.env.SEAGULL_INTEGRATION_DATA,
    SEAGULL_TEST_PYTHON:process.env.SEAGULL_TEST_PYTHON || 'python'}
}).catch(error=>{console.error(error);process.exitCode=1;});
