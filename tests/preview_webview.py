"""Browser-only renderer QA harness; not shipped in the extension."""
import json
from pathlib import Path
import shutil
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from service import Service

root = Path(__file__).resolve().parents[1]
folder = root/'work'/'webview-preview'
folder.mkdir(parents=True, exist_ok=True)
for name in ('view.js','view.css'):
    shutil.copyfile(root/'extension'/'media'/name, folder/name)
with tempfile.TemporaryDirectory(dir=root/'work') as data:
    snapshot = dict(type='snapshot',data=Service(data).call('bootstrap'),selection=dict(mode='problem',id='a01'),language='python',busy=False)
(folder/'snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
(folder/'preview.js').write_text('''
let qaSnapshot;
function emit(message){window.dispatchEvent(new MessageEvent('message',{data:message}));}
window.acquireVsCodeApi=()=>({
  getState:()=>JSON.parse(sessionStorage.getItem('state')||'null'),
  setState:state=>sessionStorage.setItem('state',JSON.stringify(state)),
  postMessage:async message=>{
    await Promise.resolve();
    if(message.action==='ready'){qaSnapshot=await (await fetch('snapshot.json')).json();emit(qaSnapshot);return;}
    if(message.action==='cacheForm')return;
    const id=qaSnapshot.selection.id;
    if(message.action==='bookmark')qaSnapshot.data.state.progress[id]={...qaSnapshot.data.state.progress[id],bookmark:1};
    if(message.action==='saveNotes')qaSnapshot.data.state.progress[id]={...qaSnapshot.data.state.progress[id],...message.record};
    if(message.action==='saveKnowledge')qaSnapshot.data.state.knowledge[id]=message.record;
    emit(qaSnapshot);emit({type:'ack',requestId:message.requestId});
  }
});
document.getElementById('theme').onclick=()=>{document.body.classList.toggle('dark');};
document.getElementById('knowledge').onclick=()=>{qaSnapshot.selection={mode:'knowledge',id:'k01'};emit(qaSnapshot);};
document.getElementById('problem').onclick=()=>{qaSnapshot.selection={mode:'problem',id:'a01'};emit(qaSnapshot);};
''',encoding='utf-8')
(folder/'index.html').write_text('''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Seagull 阅读面板检查</title><link href="view.css" rel="stylesheet"><style>
:root{--vscode-font-family:"Segoe UI","Microsoft YaHei",sans-serif;--vscode-font-size:13px;--vscode-editor-font-family:Consolas,monospace;--vscode-editor-font-size:13px;--vscode-editor-background:#fff;--vscode-editor-foreground:#333;--vscode-foreground:#333;--vscode-descriptionForeground:#616161;--vscode-panel-border:#ddd;--vscode-button-background:#0078d4;--vscode-button-foreground:#fff;--vscode-button-hoverBackground:#005a9e;--vscode-button-secondaryBackground:#e5e5e5;--vscode-button-secondaryForeground:#333;--vscode-button-secondaryHoverBackground:#ccc;--vscode-focusBorder:#0078d4;--vscode-textLink-foreground:#006ab1;--vscode-textCodeBlock-background:#f3f3f3;--vscode-input-background:#fff;--vscode-input-foreground:#333;--vscode-input-border:#ccc;--vscode-errorForeground:#a1260d;--vscode-toolbar-hoverBackground:#eee;}
.dark{--vscode-editor-background:#1f1f1f;--vscode-editor-foreground:#ccc;--vscode-foreground:#ccc;--vscode-descriptionForeground:#aaa;--vscode-panel-border:#444;--vscode-button-secondaryBackground:#3a3d41;--vscode-button-secondaryForeground:#fff;--vscode-textCodeBlock-background:#2b2b2b;--vscode-input-background:#313131;--vscode-input-foreground:#fff;--vscode-input-border:#555;--vscode-textLink-foreground:#4daafc;--vscode-toolbar-hoverBackground:#333;}
#qa{padding:8px 14px;border-bottom:1px solid #888;display:flex;gap:8px;flex-wrap:wrap;}#qa span{width:100%;font-size:11px;}
</style></head><body><div id="qa"><span>浏览器渲染检查 · 与插件共用阅读面板资源</span><button id="theme">切换主题</button><button id="knowledge">检查问答</button><button id="problem">检查题目</button></div><main id="app"></main><script src="preview.js"></script><script src="view.js"></script></body></html>''',encoding='utf-8')
print(folder)
