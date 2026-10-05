import * as vscode from 'vscode';
import * as path from 'node:path';
import {existsSync} from 'node:fs';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {CoreBridge} from './core';
import {PracticeDocuments} from './documents';
import {PracticeTree, Filter} from './tree';
import {ReadingView, Selection} from './view';
import {Bootstrap, Language, JudgeResult, Submission} from './types';

let active: PracticeExtension | undefined;
export async function activate(context: vscode.ExtensionContext): Promise<PracticeExtension> {
  active = new PracticeExtension(context);
  await active.activate();
  return active;
}
export async function deactivate(): Promise<void> {await active?.shutdown(); active = undefined;}

export class PracticeExtension {
  readonly tree = new PracticeTree();
  private output = vscode.window.createOutputChannel('Seagull');
  private core?: CoreBridge;
  private documents?: PracticeDocuments;
  private initPromise?: Promise<void>;
  private data?: Bootstrap;
  private selection?: Selection;
  private view: ReadingView;
  private language: Language;
  private result?: JudgeResult;
  private busy = false;
  private treeView?: vscode.TreeView<unknown>;
  private lastDocument?: vscode.TextDocument;
  private stopped = false;
  private selectionEpoch = 0;
  private readonlyRefs = new Map<string,string>();
  private forms: Record<string,unknown> = {};
  private formsChain: Promise<void> = Promise.resolve();
  constructor(private context: vscode.ExtensionContext) {
    this.language = context.globalState.get<Language>('language','python');
    this.tree.language = this.language;
    this.view = new ReadingView(context.extensionUri,message => this.receive(message),error => this.report(error));
  }
  async activate(): Promise<void> {
    const treeView = vscode.window.createTreeView('seagull.problems',{treeDataProvider:this.tree,showCollapseAll:true});
    this.treeView = treeView;
    const reg = (name: string, fn: (...args: any[]) => unknown) => this.context.subscriptions.push(
      vscode.commands.registerCommand(`seagull.${name}`,async (...args) => {try {return await fn(...args);} catch(error) {this.report(error); throw error;}}));
    reg('open',() => this.pick());
    reg('select',(mode: Selection['mode'],id: string) => this.select(mode,id));
    reg('run',() => this.run('run'));
    reg('submit',() => this.run('submit'));
    reg('language',() => this.switchLanguage());
    reg('filter',() => this.filter());
    reg('refresh',() => this.refresh());
    reg('history',() => this.history());
    reg('solution',() => this.solution());
    reg('resolveDraft',async () => {await this.ensure(); const doc=this.practiceDocument(); await this.documents!.resolve(doc);});
    reg('export',() => this.exportBackup());
    reg('import',() => this.importBackup());
    reg('storage',async () => {await this.ensure(); const answer=await vscode.window.showInformationMessage(`Seagull 数据目录：${this.data!.environment.data_dir}`,'在文件管理器打开'); if(answer)await vscode.commands.executeCommand('revealFileInOS',vscode.Uri.file(this.data!.environment.data_dir));});
    reg('restart',() => this.restart());
    const provider: vscode.TextDocumentContentProvider = {provideTextDocumentContent:uri => this.readonlyRefs.get(uri.toString()) ?? ''};
    this.context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider('seagull-reference',provider));
    this.context.subscriptions.push(this.tree,this.view,this.output,treeView,
      treeView.onDidChangeVisibility(e => {if(e.visible)void this.ensure().catch(error=>this.report(error));}),
      vscode.window.onDidChangeActiveTextEditor(editor => {
        const identified = this.documents?.identify(editor?.document);
        if (identified && editor) this.lastDocument=editor.document;
        void vscode.commands.executeCommand('setContext','seagull.isPractice',!!identified);
      }),
      vscode.workspace.onDidChangeConfiguration(e => {
        if(e.affectsConfiguration('seagull'))void vscode.window.showInformationMessage('Seagull 配置已修改。重启核心后生效；数据目录变更不会自动迁移记录。','重启核心').then(choice=>{if(choice)void this.restart().catch(error=>this.report(error));});
      })
    );
    if(treeView.visible)await this.ensure();
  }
  private report(error: unknown): void {
    const message=error instanceof Error ? error.message : String(error);
    this.output.appendLine(message);
    void vscode.window.showErrorMessage(`Seagull：${message}`);
  }
  private configuration(name: string, fallback: string): string {
    const config=vscode.workspace.getConfiguration('seagull');
    if(vscode.workspace.isTrusted)return config.get<string>(name,fallback);
    // Workspace values may specify executables: only user settings are used before trust.
    return config.inspect<string>(name)?.globalValue ?? fallback;
  }
  private storagePath(): string {
    const configured=this.configuration('dataDirectory','');
    if(configured) {
      if(!path.isAbsolute(configured))throw new Error('seagull.dataDirectory 必须是绝对路径');
      return path.resolve(configured);
    }
    if(process.platform==='win32' && existsSync('D:\\'))return 'D:\\SeagullPractice';
    return this.context.globalStorageUri.fsPath;
  }
  async ensure(): Promise<void> {
    if(this.stopped)throw new Error('插件已关闭');
    if(this.data)return;
    if(this.initPromise)return this.initPromise;
    this.initPromise=(async()=>{
      const dataDir=this.storagePath();
      await mkdir(dataDir,{recursive:true});
      const bridge=new CoreBridge({python:this.configuration('pythonPath','python'),
        script:path.join(this.context.extensionPath,'python','worker.py'),dataDir,
        rustc:this.configuration('rustcPath','') || undefined,log:message=>this.output.appendLine(message)});
      this.core=bridge;
      try {
        const data:Bootstrap=await bridge.request('bootstrap');
        try {this.forms=JSON.parse(await readFile(path.join(dataDir,'pending-forms.json'),'utf8'));} catch {this.forms={};}
        this.data=data;this.tree.data=data;
        this.documents=new PracticeDocuments(bridge,dataDir,data.problems,message=>this.output.appendLine(message));
        this.tree.refresh();
        if(this.treeView) {
          const passed=data.problems.filter(p=>data.state.statuses[`${p.id}:${this.language}`]==='已通过').length;
          this.treeView.description=`${this.language} · ${passed}/${data.problems.length}`;
        }
        this.output.appendLine(`Python ${data.environment.python} / 数据目录 ${data.environment.data_dir}`);
      } catch(error) {bridge.dispose();this.core=undefined;throw error;}
    })();
    try {await this.initPromise;} finally {this.initPromise=undefined;}
  }
  private update(show=false): void {
    if(!this.data || !this.selection)return;
    const snapshot={data:this.data,selection:this.selection,language:this.language,result:this.result,busy:this.busy,forms:this.forms};
    if(show)this.view.show(snapshot);else this.view.update(snapshot);
    if(this.treeView) {
      const passed=this.data.problems.filter(p=>this.data!.state.statuses[`${p.id}:${this.language}`]==='已通过').length;
      this.treeView.description=`${this.language} · ${passed}/${this.data.problems.length}`;
    }
  }
  async select(mode: Selection['mode'], id: string): Promise<vscode.TextDocument | undefined> {
    await this.ensure();
    const collection=mode==='problem'?this.data!.problems:mode==='lesson'?this.data!.lessons:mode==='knowledge'?this.data!.knowledge:[];
    if(!collection.some(p=>p.id===id))throw new Error('选择的题目不存在');
    const epoch = ++this.selectionEpoch;
    this.selection={mode,id}; this.result=undefined;
    let document: vscode.TextDocument|undefined;
    if(mode==='problem') {
      const p=this.data!.problems.find(p=>p.id===id)!;
      document=await this.documents!.open(p,this.language);
      if (epoch !== this.selectionEpoch) return document;
      this.lastDocument=document;
      await vscode.window.showTextDocument(document,{viewColumn:vscode.ViewColumn.One,preview:false});
      await vscode.commands.executeCommand('setContext','seagull.isPractice',true);
    }
    this.update(true);
    return document;
  }
  private async pick(): Promise<void> {
    await this.ensure();
    const entries=this.data!.problems.map(p=>({label:`${String(p.number).padStart(2,'0')} ${p.title}`,description:p.topic,detail:this.data!.state.statuses[`${p.id}:${this.language}`]??'未开始',id:p.id}));
    const choice=await vscode.window.showQuickPick(entries,{placeHolder:'搜索题号、题名或专题',matchOnDescription:true});
    if(choice)await this.select('problem',choice.id);
  }
  async switchLanguage(language?: Language): Promise<void> {
    await this.ensure();
    const chosen=language??await vscode.window.showQuickPick(['python','rust'],{placeHolder:'选择练习语言'}) as Language|undefined;
    if(!chosen)return;
    if(!['python','rust'].includes(chosen))throw new Error('语言不支持');
    this.language=chosen;this.tree.language=chosen;
    await this.context.globalState.update('language',chosen);this.tree.refresh();
    if(this.selection?.mode==='problem')await this.select('problem',this.selection.id);
    else this.update();
  }
  private async filter(): Promise<void> {
    await this.ensure();
    const options:Filter[]=['全部','收藏','待复习','未开始','尝试中','已通过'];
    const choice=await vscode.window.showQuickPick([...options,'按关键词搜索'],{placeHolder:'筛选算法题；背景知识与问答仍显示'});
    if(!choice)return;
    if(choice==='按关键词搜索') {
      const search=await vscode.window.showInputBox({prompt:'题号、题名或专题；清空可取消搜索',value:this.tree.search});
      if(search===undefined)return;this.tree.search=search;
    } else {this.tree.filter=choice as Filter;this.tree.search='';}
    this.tree.refresh();
  }
  async refresh(): Promise<void> {
    await this.ensure();
    this.data!.state=await this.core!.request('state');this.tree.refresh();this.update();
  }
  private practiceDocument(): vscode.TextDocument {
    const current=vscode.window.activeTextEditor?.document;
    const document=this.documents?.identify(current)?current:this.lastDocument;
    if(!document || document.isClosed || !this.documents?.identify(document))throw new Error('请先从 Seagull 打开一道算法题');
    return document;
  }
  async run(mode:'run'|'submit', document?: vscode.TextDocument): Promise<JudgeResult> {
    await this.ensure();
    if(!vscode.workspace.isTrusted)throw new Error('当前工作区未受信任；受信任后才能运行练习代码');
    if(vscode.env.remoteName)throw new Error('首版只支持本地桌面执行，请在本地窗口打开练习');
    if(this.busy)throw new Error('已有判题任务正在执行');
    const doc=document??this.practiceDocument(), identity=this.documents!.identify(doc);
    if(!identity)throw new Error('当前文件不是 Seagull 练习文件');
    // Capture before awaiting storage. Never submit a later edit accidentally.
    const code=doc.getText();
    if(Buffer.byteLength(code)>100000)throw new Error('代码不能超过 100 KB');
    this.busy=true;this.update();
    try {
      // A conflicting draft does not prevent an immutable submission snapshot.
      await this.documents!.save(doc).catch(error=>this.output.appendLine(`草稿未同步；提交当前编辑器快照：${String(error)}`));
      const response=await vscode.window.withProgress({location:vscode.ProgressLocation.Notification,title:mode==='run'?'Seagull 运行示例':'Seagull 提交代码',cancellable:true},async (_progress, token)=>{
        let requestId:string|undefined, cancelled=false;
        const listener=token.onCancellationRequested(()=>{
          cancelled=true;
          if(requestId)void this.core!.request('cancel',{request_id:requestId}).catch(error=>this.output.appendLine(String(error)));
        });
        try {
          return await this.core!.request('judge',{...identity,code,mode},45000,id=>{
            requestId=id;
            if(cancelled)void this.core!.request('cancel',{request_id:id}).catch(()=>{});
          });
        } finally {listener.dispose();}
      });
      this.data!.state=response.state;this.tree.refresh();
      if(this.selection?.mode==='problem' && this.selection.id===identity.id && this.language===identity.language)this.result=response.result;
      this.output.appendLine(`${identity.id} / ${identity.language} / ${mode}：${response.result.status} ${response.result.passed}/${response.result.total}`);
      if(response.result.stderr)this.output.appendLine(response.result.stderr);
      return response.result;
    } finally {this.busy=false;this.update(true);}
  }
  async reference(code: string, language: Language): Promise<vscode.TextDocument> {
    const uri=vscode.Uri.parse(`seagull-reference:/${Date.now()}-${Math.random().toString(36).slice(2)}/solution.${language==='rust'?'rs':'py'}`);
    this.readonlyRefs.set(uri.toString(),code);
    const doc=await vscode.workspace.openTextDocument(uri);
    return vscode.languages.setTextDocumentLanguage(doc,language==='rust'?'rust':'python');
  }
  private async solution(document?: vscode.TextDocument): Promise<void> {
    await this.ensure();const doc=document??this.practiceDocument(),identity=this.documents!.identify(doc)!;
    const answer=await this.core!.request('solution',identity);
    const reference=await this.reference(answer.code,identity.language);
    await vscode.commands.executeCommand('vscode.diff',reference.uri,doc.uri,'参考答案 ↔ 当前练习',{preview:true});
    await this.refresh();
  }
  private async history(document?: vscode.TextDocument): Promise<void> {
    await this.ensure();const doc=document??this.practiceDocument(),identity=this.documents!.identify(doc)!;
    const {history}: {history:Submission[]}=await this.core!.request('history',identity);
    if(!history.length){void vscode.window.showInformationMessage('这道题当前语言还没有运行或提交记录。');return;}
    const choice=await vscode.window.showQuickPick(history.map(record=>({label:`${record.result.status} · ${record.mode==='submit'?'提交':'示例'} · ${new Date(record.created_at).toLocaleString()}`,description:`${record.result.passed}/${record.result.total}`,record})),{placeHolder:'选择记录，查看结果与代码差异'});
    if(!choice)return;
    const reference=await this.reference(choice.record.code,identity.language);
    await vscode.commands.executeCommand('vscode.diff',reference.uri,doc.uri,'历史代码 ↔ 当前练习',{preview:true});
    this.result=choice.record.result;this.selection={mode:'problem',id:identity.id};this.update(true);
    const action=await vscode.window.showInformationMessage('已打开历史代码差异。替换会修改当前草稿，可在编辑器撤销。','替换当前草稿');
    if(action)await this.documents!.replace(doc,choice.record.code);
  }
  private async exportBackup(): Promise<void> {
    await this.ensure();await this.documents!.flush();
    const folder=path.join(this.data!.environment.data_dir,'backups');await mkdir(folder,{recursive:true});
    const destination=await vscode.window.showSaveDialog({defaultUri:vscode.Uri.file(path.join(folder,`seagull-${new Date().toISOString().replace(/[:.]/g,'-')}.json`)),filters:{'Seagull 备份':['json']}});
    if(!destination)return;
    const result=await this.core!.request('export');
    await vscode.workspace.fs.writeFile(destination,Buffer.from(JSON.stringify(result,null,2),'utf8'));
    void vscode.window.showInformationMessage(`已导出备份：${destination.fsPath}`);
  }
  private async importBackup(): Promise<void> {
    await this.ensure();await this.documents!.flush();
    const selected=await vscode.window.showOpenDialog({canSelectMany:false,filters:{'Seagull 备份或旧数据库':['json','sqlite3']},title:'导入 JSON 备份或旧版 practice.sqlite3（只读迁移）'});
    if(!selected?.length)return;
    const source=selected[0];if(source.scheme!=='file')throw new Error('请选择本机备份文件');
    const size=(await vscode.workspace.fs.stat(source)).size;
    if(size>20_000_000)throw new Error('导入文件超过 20 MB');
    let result;
    if(source.fsPath.endsWith('.sqlite3'))result=await this.core!.request('importDatabase',{path:source.fsPath});
    else result=await this.core!.request('import',JSON.parse(Buffer.from(await vscode.workspace.fs.readFile(source)).toString('utf8')));
    await this.refresh();
    void vscode.window.showInformationMessage(`已合并 ${result.imported} 条记录；导入前备份：${result.backup}。已打开的草稿不会被覆盖，重新打开或解决冲突后采用新记录。`);
  }
  private async receive(message: any): Promise<void> {
    await this.ensure();
    const selection:Selection=message.selection;
    // Form cache messages may arrive after a selection change. Validate their own identity.
    if(message.action==='cacheForm') {
      const valid=selection?.mode==='problem'?this.data!.problems.some(p=>p.id===selection.id):selection?.mode==='knowledge'&&this.data!.knowledge.some(k=>k.id===selection.id);
      if(!valid || !message.record || Buffer.byteLength(JSON.stringify(message.record))>100000)throw new Error('待保存表单格式错误');
      this.forms[`${selection.mode}:${selection.id}`]=message.record;
      await this.persistForms();return;
    }
    if(!selection || !this.selection || selection.mode!==this.selection.mode || selection.id!==this.selection.id)throw new Error('题目已切换，请在当前面板重试');
    const action=message.action;
    if(['run','submit','openEditor','language','solution','history','bookmark','saveNotes'].includes(action) && selection.mode!=='problem')throw new Error('该操作仅适用于算法题');
    if(action==='openEditor'){await this.select('problem',selection.id);return;}
    if(action==='language'){await this.switchLanguage(this.language==='python'?'rust':'python');return;}
    if(action==='run'||action==='submit') {
      // Reading-panel buttons always operate on that panel's problem, never a different active file.
      const doc=await this.documents!.open(this.data!.problems.find(p=>p.id===selection.id)!,this.language);
      this.lastDocument=doc;await this.run(action==='run'?'run':'submit',doc);return;
    }
    if(action==='history'||action==='solution') {
      const doc=await this.documents!.open(this.data!.problems.find(p=>p.id===selection.id)!,this.language);
      if(action==='history')await this.history(doc);else await this.solution(doc);return;
    }
    if(action==='bookmark') {
      await this.core!.request('progress',{id:selection.id,changes:{bookmark:this.data!.state.progress[selection.id]?.bookmark?0:1}});
    } else if(action==='saveNotes') {
      const record=message.record;
      if(!record || typeof record.notes!=='string')throw new Error('笔记格式错误');
      await this.core!.request('progress',{id:selection.id,changes:{notes:record.notes,mastery:record.mastery,review_at:record.review_at||null}});
      if(JSON.stringify(this.forms[`problem:${selection.id}`])===JSON.stringify(record))delete this.forms[`problem:${selection.id}`];
      await this.persistForms();
    } else if(action==='saveKnowledge') {
      if(selection.mode!=='knowledge')throw new Error('知识题类型错误');
      await this.core!.request('knowledge',{id:selection.id,answer:message.record?.answer,mastery:message.record?.mastery});
      if(JSON.stringify(this.forms[`knowledge:${selection.id}`])===JSON.stringify(message.record))delete this.forms[`knowledge:${selection.id}`];
      await this.persistForms();
    } else throw new Error('面板操作不支持');
    await this.refresh();
  }
  private async persistForms(): Promise<void> {
    const snapshot=JSON.stringify(this.forms);
    const destination=path.join(this.data!.environment.data_dir,'pending-forms.json');
    this.formsChain=this.formsChain.catch(()=>{}).then(()=>writeFile(destination,snapshot,'utf8'));
    await this.formsChain;
  }
  async restart(): Promise<void> {
    if(this.busy)throw new Error('请先取消或等待当前判题，再重启核心');
    try {await this.documents?.flush();} catch(error) {this.output.appendLine(`重启前未同步代码保留在恢复副本中：${String(error)}`);}
    this.documents?.dispose();this.core?.dispose();
    this.data=undefined;this.documents=undefined;this.core=undefined;this.lastDocument=undefined;
    await this.ensure();if(this.selection)await this.select(this.selection.mode,this.selection.id);
  }
  async shutdown(): Promise<void> {
    if(this.stopped)return;
    this.stopped=true;
    await this.formsChain.catch(()=>{});
    try {await this.documents?.flush();} catch(error) {this.output.appendLine(`关闭前数据库同步失败；恢复副本保留：${String(error)}`);}
    this.documents?.dispose();this.core?.dispose();
  }
  // Exposed API used by real Extension Development Host integration tests.
  async api(method: string, params?: unknown): Promise<any> {
    await this.ensure();
    if(method==='judge' && (!vscode.workspace.isTrusted || vscode.env.remoteName))throw new Error('当前窗口不支持执行练习代码');
    return this.core!.request(method,params);
  }
}
