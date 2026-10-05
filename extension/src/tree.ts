import * as vscode from 'vscode';
import {Bootstrap, Language, Problem, State} from './types';

export type Filter = '全部' | '收藏' | '待复习' | '未开始' | '尝试中' | '已通过';
type Node = {kind: 'group'; label: string; children: Node[]} | {kind: 'item'; label: string; id: string; mode: 'problem' | 'lesson' | 'knowledge'; problem?: Problem};
export class PracticeTree implements vscode.TreeDataProvider<Node> {
  private changed = new vscode.EventEmitter<Node | undefined>();
  readonly onDidChangeTreeData = this.changed.event;
  data?: Bootstrap;
  language: Language = 'python';
  filter: Filter = '全部';
  search = '';
  refresh(state?: State): void { if (state && this.data) this.data.state = state; this.changed.fire(undefined); }
  getTreeItem(node: Node): vscode.TreeItem {
    const item = new vscode.TreeItem(node.label, node.kind === 'group' ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None);
    if (node.kind === 'group') { item.description = String(node.children.length); return item; }
    item.id = `${node.mode}:${node.id}`;
    item.command = {command: 'seagull.select', title: '打开练习', arguments: [node.mode, node.id]};
    if (node.problem) {
      const st = this.data?.state.statuses[`${node.id}:${this.language}`] ?? '未开始';
      const progress = this.data?.state.progress[node.id];
      item.description = `${st}${progress?.bookmark ? ' ★' : ''}${this.due(node.id) ? ' · 待复习' : ''}`;
      item.iconPath = new vscode.ThemeIcon(st === '已通过' ? 'pass' : st === '尝试中' ? 'circle-filled' : 'circle-outline');
      item.tooltip = `${node.problem.title}\n${node.problem.topic} / ${this.language} / ${node.problem.difficulty}`;
    } else item.iconPath = new vscode.ThemeIcon(node.mode === 'lesson' ? 'book' : 'comment-discussion');
    return item;
  }
  private due(id: string): boolean {
    const p = this.data?.state.progress[id];
    const d = new Date(), today = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    return p?.mastery === '需要重做' || !!(p?.review_at && p.review_at <= today);
  }
  getChildren(node?: Node): Node[] {
    if (node) return node.kind === 'group' ? node.children : [];
    if (!this.data) return [];
    const groups = new Map<string, Node[]>();
    for (const p of this.data.problems) {
      const progress = this.data.state.progress[p.id];
      const status = this.data.state.statuses[`${p.id}:${this.language}`] ?? '未开始';
      if (this.search && !`${p.number} ${p.title} ${p.topic}`.toLowerCase().includes(this.search.toLowerCase())) continue;
      if (this.filter === '收藏' && !progress?.bookmark || this.filter === '待复习' && !this.due(p.id)) continue;
      if (['未开始','尝试中','已通过'].includes(this.filter) && this.filter !== status) continue;
      if (!groups.has(p.topic)) groups.set(p.topic, []);
      groups.get(p.topic)!.push({kind:'item', label:`${String(p.number).padStart(2,'0')} ${p.title}`, id:p.id, mode:'problem', problem:p});
    }
    const result: Node[] = [...groups].map(([label, children]) => ({kind:'group', label, children}));
    result.push({kind:'group', label:'背景知识', children:this.data.lessons.map(l => ({kind:'item',label:l.title,id:l.id,mode:'lesson'}))});
    result.push({kind:'group', label:'后训练问答', children:this.data.knowledge.map(k => ({kind:'item',label:k.title,id:k.id,mode:'knowledge'}))});
    return result;
  }
  dispose(): void {this.changed.dispose();}
}
