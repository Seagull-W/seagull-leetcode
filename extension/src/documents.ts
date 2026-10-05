import * as vscode from 'vscode';
import {randomUUID} from 'node:crypto';
import {mkdir, readFile, writeFile, unlink, readdir} from 'node:fs/promises';
import * as path from 'node:path';
import {CoreBridge, RpcError} from './core';
import {Draft, Language, Problem} from './types';

interface Session {
  id: string; language: Language; uri: vscode.Uri; revision: string | null;
  timer?: NodeJS.Timeout; chain: Promise<void>; conflict: boolean; recovery: string; savedText?: string;
}
interface Recovery {code: string; expected: string | null; updated_at: string}

/** TextDocument is authoritative while open; SQLite stores recovery drafts and immutable submissions. */
export class PracticeDocuments implements vscode.Disposable {
  private sessions = new Map<string, Session>();
  private listeners: vscode.Disposable[];
  private owner = randomUUID();
  private disposed = false;
  private recoveryChain = new Map<string, Promise<void>>();
  private opening = new Map<string, Promise<vscode.TextDocument>>();
  constructor(private core: CoreBridge, readonly dataDir: string, private problems: Problem[], private log: (message: string) => void) {
    this.listeners = [
      vscode.workspace.onDidChangeTextDocument(e => {
        const session = this.session(e.document);
        if (!session || !e.contentChanges.length) return;
        const code = e.document.getText();
        // A disk recovery copy survives worker failure and drafts with concurrent edits.
        void this.recover(session, code).catch(error => this.log(`恢复副本保存失败：${String(error)}`));
        if (session.timer) clearTimeout(session.timer);
        session.timer = setTimeout(() => {void this.save(e.document).catch(error => this.log(String(error)));}, 600);
      }),
      vscode.workspace.onDidSaveTextDocument(doc => {if (this.session(doc)) void this.save(doc).catch(error => this.log(String(error)));}),
      vscode.workspace.onDidCloseTextDocument(doc => {
        const session = this.session(doc);
        if (!session) return;
        if (session.timer) clearTimeout(session.timer);
        // The final document value is captured before removing the editor association.
        void this.save(doc).catch(error => this.log(String(error))).finally(() => this.sessions.delete(doc.uri.toString()));
      })
    ];
  }
  private session(doc: vscode.TextDocument): Session | undefined {return this.sessions.get(doc.uri.toString());}
  identify(doc?: vscode.TextDocument): {id: string; language: Language} | undefined {
    if (!doc) return;
    const tracked = this.session(doc);
    if (tracked) return {id:tracked.id, language:tracked.language};
    if (doc.uri.scheme !== 'file') return;
    const relative = path.relative(path.join(this.dataDir,'solutions'), doc.uri.fsPath).split(path.sep);
    if (relative.length !== 2 || !this.problems.some(p => p.id === relative[0])) return;
    const language = relative[1] === 'solution.py' ? 'python' : relative[1] === 'solution.rs' ? 'rust' : undefined;
    if (language) return {id:relative[0], language};
  }
  private async recover(s: Session, code: string): Promise<void> {
    const previous = this.recoveryChain.get(s.recovery) ?? Promise.resolve();
    const snapshot: Recovery = {code, expected:s.revision, updated_at:new Date().toISOString()};
    const operation = previous.catch(() => {}).then(async () => {
      await mkdir(path.dirname(s.recovery), {recursive:true});
      await writeFile(s.recovery, JSON.stringify(snapshot), 'utf8');
    });
    this.recoveryChain.set(s.recovery, operation);
    await operation;
  }
  private async recoveries(id: string, language: Language): Promise<{file: string; record: Recovery}[]> {
    const base = path.join(this.dataDir,'recovery'), result: {file:string; record:Recovery}[] = [];
    let owners: string[];
    try {owners = await readdir(base);} catch {return result;}
    for (const owner of owners) {
      const file = path.join(base,owner,`${id}-${language}.json`);
      try {
        const record = JSON.parse(await readFile(file,'utf8'));
        if (typeof record.code === 'string' && Buffer.byteLength(record.code) <= 100000 && typeof record.updated_at === 'string') result.push({file,record});
      } catch { /* Other files or unfinished writes are ignored; no data is deleted. */ }
    }
    return result.sort((a,b) => b.record.updated_at.localeCompare(a.record.updated_at));
  }
  async open(problem: Problem, language: Language): Promise<vscode.TextDocument> {
    const key = `${problem.id}:${language}`;
    const pending = this.opening.get(key);
    if (pending) return pending;
    const operation = this.openOne(problem,language);
    this.opening.set(key,operation);
    try {return await operation;} finally {this.opening.delete(key);}
  }
  private async openOne(problem: Problem, language: Language): Promise<vscode.TextDocument> {
    if (this.disposed) throw new Error('编辑器管理器已关闭');
    const uri = vscode.Uri.file(path.join(this.dataDir,'solutions',problem.id,language === 'rust' ? 'solution.rs' : 'solution.py'));
    const existing = vscode.workspace.textDocuments.find(d => d.uri.toString() === uri.toString());
    if (existing && this.session(existing)) return existing;
    const {draft}: {draft:Draft|null} = await this.core.request('draft',{id:problem.id,language});
    let code = draft?.code ?? problem.templates[language];
    const copies = await this.recoveries(problem.id,language);
    const recovered = copies.find(r => r.record.code !== code);
    let restored: Recovery | undefined;
    if (recovered && !existing?.isDirty) {
      const choice = await vscode.window.showWarningMessage('发现尚未同步的练习代码；恢复副本保留在数据目录中。', '恢复到编辑器','使用数据库草稿');
      if (choice === '恢复到编辑器') {code = recovered.record.code; restored = recovered.record;}
    }
    await mkdir(path.dirname(uri.fsPath),{recursive:true});
    // Never overwrite a dirty buffer recreated by VS Code hot exit.
    if (!existing) await writeFile(uri.fsPath,code,'utf8');
    else if (!existing.isDirty && existing.getText() !== code) {
      const edit = new vscode.WorkspaceEdit();
      edit.replace(existing.uri,new vscode.Range(existing.positionAt(0),existing.positionAt(existing.getText().length)),code);
      if (!await vscode.workspace.applyEdit(edit)) throw new Error('草稿恢复到编辑器失败');
    }
    const document = existing ?? await vscode.workspace.openTextDocument(uri);
    const hotExitCopy = existing?.isDirty ? copies.find(r => r.record.code === document.getText())?.record : undefined;
    const hasDifferentBuffer = document.getText() !== draft?.code && !!existing?.isDirty;
    const restoreConflict = hasDifferentBuffer ? !hotExitCopy || hotExitCopy.expected !== (draft?.updated_at ?? null)
      : !!restored && restored.expected !== (draft?.updated_at ?? null);
    const s: Session = {id:problem.id,language,uri,revision:draft?.updated_at ?? null,chain:Promise.resolve(),conflict:false,
      recovery:path.join(this.dataDir,'recovery',this.owner,`${problem.id}-${language}.json`),savedText:draft?.code};
    s.conflict = restoreConflict;
    this.sessions.set(uri.toString(),s);
    if (document.getText() !== draft?.code) await this.save(document).catch(error => this.log(String(error)));
    return document;
  }
  async save(doc: vscode.TextDocument): Promise<void> {
    const s = this.session(doc);
    if (!s) return;
    if (s.timer) {clearTimeout(s.timer); s.timer = undefined;}
    const code = doc.getText();
    if (s.savedText === code) return s.chain;
    await this.recover(s,code);
    const operation = s.chain.catch(() => {}).then(async () => {
      if (s.conflict) throw new RpcError('conflict','草稿冲突尚未解决；使用 Seagull: 比较并解决草稿冲突。');
      if (s.savedText === code) return;
      try {
        const result = await this.core.request('saveDraft',{id:s.id,language:s.language,code,expected:s.revision});
        s.revision = result.saved_at; s.savedText = code;
        // Wait for any queued recovery write before deleting exactly this window's copy.
        if (doc.getText() === code) {
          await this.recoveryChain.get(s.recovery)?.catch(() => {});
          if (doc.getText() === code) await unlink(s.recovery).catch(() => {});
        }
      } catch (error) {
        if (error instanceof RpcError && error.code === 'conflict') {
          s.conflict = true;
          void vscode.window.showWarningMessage('Seagull 草稿被另一个窗口更新。当前代码及恢复副本均保留，请运行“比较并解决草稿冲突”。');
        }
        throw error;
      }
    });
    s.chain = operation;
    await operation;
  }
  async compare(doc: vscode.TextDocument, code: string, title: string): Promise<void> {
    const reference = await vscode.workspace.openTextDocument({content:code,language:doc.languageId});
    await vscode.commands.executeCommand('vscode.diff',reference.uri,doc.uri,title,{preview:true});
  }
  async resolve(doc: vscode.TextDocument): Promise<void> {
    const s = this.session(doc); if (!s) throw new Error('请先打开 Seagull 练习文件');
    await s.chain.catch(() => {});
    const {draft}: {draft:Draft|null} = await this.core.request('draft',{id:s.id,language:s.language});
    await this.compare(doc,draft?.code ?? '', '数据库草稿 ↔ 当前编辑器');
    const action = await vscode.window.showWarningMessage('已打开差异比较。选择要保存的版本；取消会保留双方代码。',{modal:true},'保留当前编辑器','采用数据库草稿');
    if (!action) return;
    s.revision = draft?.updated_at ?? null; s.conflict = false;
    if (action === '采用数据库草稿') {
      await this.replace(doc,draft?.code ?? '');
    }
    await this.save(doc);
  }
  async replace(doc: vscode.TextDocument, code: string): Promise<void> {
    const edit = new vscode.WorkspaceEdit();
    edit.replace(doc.uri,new vscode.Range(doc.positionAt(0),doc.positionAt(doc.getText().length)),code);
    if (!await vscode.workspace.applyEdit(edit)) throw new Error('编辑器替换失败');
    await this.save(doc);
  }
  async flush(): Promise<void> {
    for (const doc of vscode.workspace.textDocuments) if (this.session(doc)) await this.save(doc);
  }
  dispose(): void {
    this.disposed = true;
    for (const listener of this.listeners) listener.dispose();
    for (const s of this.sessions.values()) if (s.timer) clearTimeout(s.timer);
  }
}
