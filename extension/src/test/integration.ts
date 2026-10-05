import * as vscode from 'vscode';
import * as assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
import * as path from 'node:path';
import {PracticeExtension} from '../extension';

async function replace(doc:vscode.TextDocument,code:string):Promise<void> {
  const edit=new vscode.WorkspaceEdit();edit.replace(doc.uri,new vscode.Range(doc.positionAt(0),doc.positionAt(doc.getText().length)),code);
  assert.equal(await vscode.workspace.applyEdit(edit),true);
}
export async function run():Promise<void> {
  const directory=process.env.SEAGULL_INTEGRATION_DATA!;
  await vscode.workspace.getConfiguration('seagull').update('dataDirectory',directory,vscode.ConfigurationTarget.Global);
  await vscode.workspace.getConfiguration('seagull').update('pythonPath',process.env.SEAGULL_TEST_PYTHON,vscode.ConfigurationTarget.Global);
  const extension=vscode.extensions.getExtension<PracticeExtension>('Seagull-W.seagull-practice');
  assert.ok(extension,'Extension manifest registered');
  const api=await extension.activate();
  const bootstrap=await api.api('bootstrap');assert.equal(bootstrap.problems.length,63);assert.equal(bootstrap.knowledge.length,10);
  const python=await api.select('problem','a01');assert.ok(python);assert.equal(python.languageId,'python');
  await replace(python,'def solve(nums):\n    return sorted(set(nums))\n');
  assert.equal(python.isDirty,true,'Submit must support unsaved document buffers');
  const result=await api.run('submit',python);assert.equal(result.status,'通过');assert.equal(result.passed,result.total);
  const history=await api.api('history',{id:'a01',language:'python'});assert.equal(history.history[0].code,python.getText());
  // Later edits must not alter the code snapshot stored for an earlier submission.
  await replace(python,'def solve(nums):\n    return sorted(set(nums)) # later edit\n');
  await new Promise(resolve=>setTimeout(resolve,900));
  assert.ok((await api.api('draft',{id:'a01',language:'python'})).draft.code.includes('later edit'));
  assert.equal((await api.api('history',{id:'a01',language:'python'})).history[0].code,history.history[0].code);
  await api.switchLanguage('rust');
  const rust=vscode.workspace.textDocuments.find(d=>d.uri.fsPath.endsWith('solution.rs'));assert.ok(rust);
  await replace(rust,'pub fn solve(mut nums: Vec<i64>) -> Vec<i64> { nums.dedup(); nums }\n');
  const rustResult=await api.run('submit',rust);assert.equal(rustResult.status,'通过');
  assert.equal((await api.api('draft',{id:'a01',language:'python'})).draft.code,python.getText());
  await api.api('progress',{id:'a01',changes:{notes:'插件集成测试笔记',bookmark:1,mastery:'独立完成',review_at:'2026-10-07'}});
  await api.api('knowledge',{id:'k01',answer:'只对有效回答 token 计算 loss。',mastery:'提示后完成'});
  const solution=await api.api('solution',{id:'a01',language:'rust'});
  const ref=await api.reference(solution.code,'rust');assert.equal(ref.uri.scheme,'seagull-reference');assert.equal(ref.getText(),solution.code);
  await api.select('lesson','start');await api.select('knowledge','k01');
  const pendingAnswer={answer:'未点击保存的恢复测试回答',mastery:'需要重做'};
  await (api as any).receive({action:'cacheForm',selection:{mode:'knowledge',id:'k01'},record:pendingAnswer});
  await api.restart();
  assert.deepEqual((api as any).forms['knowledge:k01'],pendingAnswer,'Unsaved forms survive a worker restart');
  await (api as any).receive({action:'saveKnowledge',selection:{mode:'knowledge',id:'k01'},record:pendingAnswer});
  assert.equal((api as any).forms['knowledge:k01'],undefined,'Successful saves clear only the matching recovery copy');
  const state=await api.api('state');assert.equal(state.progress.a01.notes,'插件集成测试笔记');assert.equal(state.progress.a01.seen_answer,1);
  assert.equal(state.statuses['a01:rust'],'已通过');assert.equal(state.statuses['a01:python'],'已通过');
  assert.equal(state.knowledge.k01.answer,pendingAnswer.answer);
  assert.ok((await stat(path.join(directory,'practice.sqlite3'))).isFile());
  const backup=await api.api('export');assert.equal(backup.tables.submissions.length,2);
  const draft=await api.api('draft',{id:'a01',language:'rust'});assert.equal(draft.draft.code,rust.getText());
  assert.equal(api.tree.getChildren().length,14,'12 topics and 2 knowledge groups');
  // Hot exit buffers cannot silently overwrite a draft changed by another process.
  await api.select('problem','a01');
  const current=await api.api('draft',{id:'a01',language:'rust'});
  await api.api('saveDraft',{id:'a01',language:'rust',code:'// another window',expected:current.draft.updated_at});
  await api.restart();
  assert.equal(rust.getText(),'pub fn solve(mut nums: Vec<i64>) -> Vec<i64> { nums.dedup(); nums }\n');
  assert.equal((await api.api('draft',{id:'a01',language:'rust'})).draft.code,'// another window');
  await api.shutdown();
  const diskCode=await readFile(path.join(directory,'solutions','a01','solution.rs'),'utf8');assert.ok(diskCode.includes('todo!'));
  console.log('Seagull integration: native editors, unsaved Python/Rust submit, snapshots, drafts, readonly references, forms, restart and hot-exit conflict PASS');
}
