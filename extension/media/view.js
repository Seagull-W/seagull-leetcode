'use strict';
const vscode = acquireVsCodeApi();
const app = document.getElementById('app');
const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty = v => esc(JSON.stringify(v,null,2));
let snapshot, sequence = 0, pending = new Map();
let ui = vscode.getState() || {tab:'problem',hints:0,forms:{}};
function persist() {vscode.setState(ui);}
function key() {return `${snapshot.selection.mode}:${snapshot.selection.id}`;}
function form() {return ui.forms[key()];}
function send(action, extra={}) {
  const requestId=String(++sequence);
  pending.set(requestId,{owner:key(),action,record:extra.record?JSON.stringify(extra.record):undefined});
  vscode.postMessage({action,requestId,selection:snapshot.selection,language:snapshot.language,...extra});
  return requestId;
}
function body(text) {return text.trim().split('\n').map(line=>line.startsWith('## ')?`<h2>${esc(line.slice(3))}</h2>`:line.trim()?`<p>${esc(line)}</p>`:'').join('');}
function status(message,error=false) {const el=document.getElementById('formStatus');if(el){el.textContent=message;el.className=error?'status error':'status';}}
function renderResult(r) {
  if(!r)return '<p class="empty">在代码编辑器中实现 solve，运行示例或提交代码后查看反馈。</p>';
  return `<section class="result"><h2>${esc(r.status)} · ${r.passed} / ${r.total}</h2><p>${esc(r.message)}</p><p class="meta">执行 ${r.execution_ms} ms / 编译 ${r.compile_ms} ms</p>${r.stderr?`<h3>编译器 / 错误信息</h3><pre>${esc(r.stderr)}</pre>`:''}${r.stdout?`<h3>调试输出</h3><pre>${esc(r.stdout)}</pre>`:''}${r.cases.map(c=>`<details ${!c.passed?'open':''}><summary>用例 ${c.index} · ${c.passed?'通过':'不匹配'}</summary><h3>输入</h3><pre>${pretty(c.input)}</pre><h3>期望</h3><pre>${pretty(c.expected)}</pre><h3>返回</h3><pre>${pretty(c.actual)}</pre></details>`).join('')}</section>`;
}
function render() {
  const {data,selection,language,busy}=snapshot;
  const content=selection.mode==='problem'?data.problems.find(p=>p.id===selection.id):selection.mode==='lesson'?data.lessons.find(l=>l.id===selection.id):data.knowledge.find(k=>k.id===selection.id);
  if(!content)return;
  if(ui.current!==key()){ui.current=key();ui.tab='problem';ui.hints=0;persist();}
  const progress=data.state.progress[selection.id]||{};
  let html=`<header><div class="meta">${selection.mode==='problem'?`${esc(content.topic)} / ${esc(language)} / ${esc(data.state.statuses[`${selection.id}:${language}`]||'未开始')}${progress.seen_answer?' / 已看解答':''}`:selection.mode==='lesson'?esc(content.topic):'大模型后训练 / 开放问答'}</div><h1>${content.number?`${String(content.number).padStart(2,'0')}　`:''}${esc(content.title)}</h1>`;
  if(selection.mode==='problem')html+=`<div class="actions"><button data-action="run" ${busy?'disabled':''}>运行示例</button><button data-action="submit" ${busy?'disabled':''}>提交代码</button><button class="secondary" data-action="language">${language==='python'?'切换 Rust':'切换 Python'}</button><button class="secondary" data-action="bookmark">${progress.bookmark?'取消收藏':'收藏'}</button></div>`;
  html+='</header>';
  if(selection.mode==='lesson')html+=body(content.body);
  else if(selection.mode==='knowledge') {
    const record=form()||data.state.knowledge[selection.id]||{answer:'',mastery:'未自评'};
    html+=`<p>${esc(content.question)}</p><label for="answer">你的解释与例子</label><textarea id="answer">${esc(record.answer)}</textarea><label for="mastery">掌握程度</label><select id="mastery">${data.mastery.map(m=>`<option ${m===record.mastery?'selected':''}>${esc(m)}</option>`).join('')}</select><p class="actions"><button data-action="saveKnowledge">保存回答</button></p><p id="formStatus" class="status">${form()?'有尚未保存的修改，关闭后可在本面板恢复。':'回答保存到本地数据库。'}</p><details><summary>参考要点</summary><ul>${content.points.map(p=>`<li>${esc(p)}</li>`).join('')}</ul></details>`;
  } else {
    const tabs=[['problem','题目'],['background','背景知识'],['hints','提示与解答'],['result','判题结果'],['notes','笔记与复习']];
    html+=`<nav aria-label="阅读内容">${tabs.map(([t,title])=>`<button data-tab="${t}" class="${ui.tab===t?'active':''}" aria-pressed="${ui.tab===t}">${title}</button>`).join('')}</nav>`;
    if(ui.tab==='problem')html+=`<p>${esc(content.description)}</p>${content.examples.map((c,i)=>`<h3>示例 ${i+1}</h3><pre>输入参数：${pretty(c.input)}\n返回结果：${pretty(c.expected)}</pre>`).join('')}<p class="meta">全部测试 ${content.test_count} 个 / 题目版本 ${content.version}</p><p class="actions"><button class="secondary" data-action="openEditor">打开代码编辑器</button><button class="secondary" data-action="history">提交历史与恢复</button></p>`;
    if(ui.tab==='background')html+=data.lessons.filter(l=>l.topic===content.topic||l.id==='start').map(l=>`<h2>${esc(l.title)}</h2>${body(l.body)}`).join('');
    if(ui.tab==='hints')html+=`${content.hints.slice(0,ui.hints).map(h=>`<p class="hint">${esc(h)}</p>`).join('')}<button data-action="hint" ${ui.hints>=content.hints.length?'disabled':''}>展开下一条提示</button><details><summary>思路、复杂度与常见错误</summary><p>${esc(content.approach)}</p><p>${esc(content.complexity)}</p><p>${esc(content.pitfalls)}</p></details><button class="secondary" data-action="solution">查看参考答案并比较</button><p class="meta">查看参考答案会留下记录。</p>`;
    if(ui.tab==='result')html+=renderResult(snapshot.result);
    if(ui.tab==='notes') {
      const record=form()||{notes:progress.notes||'',mastery:progress.mastery||'未自评',review_at:progress.review_at||''};
      html+=`<label for="notes">解题笔记</label><textarea id="notes" placeholder="记录适用条件、不变量、边界和易错点">${esc(record.notes)}</textarea><div class="form-row"><div><label for="mastery">掌握程度</label><select id="mastery">${data.mastery.map(m=>`<option ${m===record.mastery?'selected':''}>${esc(m)}</option>`).join('')}</select></div><div><label for="review">复习日期</label><input id="review" type="date" value="${esc(record.review_at)}"></div></div><p class="actions"><button data-action="saveNotes">保存笔记与复习</button><button class="secondary" data-action="tomorrow">明天复习</button><button class="secondary" data-action="history">提交历史与恢复</button></p><p id="formStatus" class="status">${form()?'有尚未保存的修改，关闭后可在本面板恢复。':'笔记保存到本地数据库。'}</p>`;
    }
  }
  html+='<footer><p class="meta">本地练习记录 · 备份与恢复可从命令面板打开</p></footer>';
  app.innerHTML=html;
  app.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{ui.tab=button.dataset.tab;persist();render();}));
  app.querySelectorAll('textarea,input,select').forEach(element=>element.addEventListener('input',()=>{capture();status('尚未保存，请点击保存。');}));
  app.querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',()=>{
    const action=button.dataset.action;
    if(action==='hint'){ui.hints++;persist();render();return;}
    if(action==='tomorrow'){const d=new Date();d.setDate(d.getDate()+1);document.getElementById('review').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;capture();status('复习日期已调整，请保存。');return;}
    if(action==='saveNotes'||action==='saveKnowledge'){capture();send(action,{record:form()});status('正在保存…');return;}
    send(action);
  }));
}
function capture() {
  if(!snapshot)return;
  const answer=document.getElementById('answer'),notes=document.getElementById('notes');
  if(answer)ui.forms[key()]={answer:answer.value,mastery:document.getElementById('mastery').value};
  if(notes)ui.forms[key()]={notes:notes.value,mastery:document.getElementById('mastery').value,review_at:document.getElementById('review').value};
  persist();
  if(answer||notes)vscode.postMessage({action:'cacheForm',selection:snapshot.selection,language:snapshot.language,record:form()});
}
window.addEventListener('message',event=>{
  const message=event.data;
  if(message.type==='snapshot'){
    if(!snapshot && message.forms)ui.forms={...message.forms,...ui.forms};
    if(snapshot&&snapshot.selection.id===message.selection.id&&JSON.stringify(message.result)!==JSON.stringify(snapshot.result)&&message.result&&!message.busy)ui.tab='result';
    snapshot=message;render();
  }
  if(message.type==='ack'){
    const operation=pending.get(message.requestId);pending.delete(message.requestId);
    // Only discard a form if the server response corresponds to the exact text sent.
    if(operation?.record&&JSON.stringify(ui.forms[operation.owner])===operation.record){delete ui.forms[operation.owner];persist();}
    if(operation&&operation.owner===key())status(operation.record?'已保存到本地数据库。':'操作已完成。');
  }
  if(message.type==='error'){pending.delete(message.requestId);status(message.message,true);}
});
vscode.postMessage({action:'ready'});
