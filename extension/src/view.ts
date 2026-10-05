import * as vscode from 'vscode';
import {randomBytes} from 'node:crypto';
import {Bootstrap, JudgeResult, Language} from './types';

export interface Selection {mode: 'problem' | 'lesson' | 'knowledge'; id: string}
export interface ViewSnapshot {data: Bootstrap; selection: Selection; language: Language; result?: JudgeResult; busy: boolean; forms?: Record<string,unknown>}
export class ReadingView implements vscode.Disposable {
  private panel?: vscode.WebviewPanel;
  private snapshot?: ViewSnapshot;
  private ready = false;
  private subscriptions: vscode.Disposable[] = [];
  constructor(private root: vscode.Uri, private receive: (message: any) => Promise<void>, private report: (e: unknown) => void) {}
  show(snapshot: ViewSnapshot): void {
    this.snapshot = snapshot;
    if (!this.panel) {
      const media = vscode.Uri.joinPath(this.root,'media');
      const panel = vscode.window.createWebviewPanel('seagull.reading','Seagull 题目与复习',
        {viewColumn:vscode.ViewColumn.Beside,preserveFocus:true},
        {enableScripts:true,localResourceRoots:[media]});
      this.panel = panel;
      const nonce = randomBytes(16).toString('hex');
      const css = panel.webview.asWebviewUri(vscode.Uri.joinPath(media,'view.css'));
      const js = panel.webview.asWebviewUri(vscode.Uri.joinPath(media,'view.js'));
      panel.webview.html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${panel.webview.cspSource}; script-src 'nonce-${nonce}';"><link rel="stylesheet" href="${css}"><title>Seagull 题目与复习</title></head><body><main id="app"><p>正在读取练习…</p></main><script nonce="${nonce}" src="${js}"></script></body></html>`;
      this.subscriptions.push(panel.webview.onDidReceiveMessage(async message => {
        if (message?.action === 'ready') {this.ready = true; this.push(); return;}
        // These messages are UI intentions, never arbitrary Python methods or filesystem paths.
        if (!message || typeof message.action !== 'string') return;
        try {await this.receive(message); if(message.requestId)await panel.webview.postMessage({type:'ack', requestId:message.requestId});}
        catch (error) {this.report(error); await panel.webview.postMessage({type:'error', requestId:message.requestId,message:String(error instanceof Error ? error.message : error)});}
      }));
      this.subscriptions.push(panel.onDidDispose(() => {this.panel = undefined; this.ready = false;}));
      this.subscriptions.push(panel.onDidChangeViewState(e => {if (e.webviewPanel.visible) this.push();}));
    } else this.panel.reveal(undefined,true);
    this.push();
  }
  update(snapshot: ViewSnapshot): void {this.snapshot = snapshot; this.push();}
  private push(): void {if (this.ready && this.snapshot) void this.panel?.webview.postMessage({type:'snapshot',...this.snapshot});}
  dispose(): void {this.panel?.dispose(); for (const disposable of this.subscriptions) disposable.dispose();}
}
