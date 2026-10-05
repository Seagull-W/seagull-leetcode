'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty = value => JSON.stringify(value, null, 2);
const app = {mode:'algorithms', language:'python', selected:null, tab:'problem', token:'', problems:[], lessons:[], knowledge:[], state:{statuses:{},progress:{},knowledge:{}}, dirty:false, busy:false, hints:{}, saveChain:Promise.resolve(), epoch:0};
let saveTimer, toastTimer, notesTimer, knowledgeTimer;
function toast(text) { $('toast').textContent=text; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,4500); }
function storageGet(key) {try{return JSON.parse(localStorage.getItem(key));}catch{return null;}}
function storageSet(key,value) {try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{return false;}}
function storageRemove(key) {try{localStorage.removeItem(key);}catch{}}
const draftKey = (id,lang) => `seagull:draft:${id}:${lang}`;
async function api(path,data) {
  const options=data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Seagull-Token':app.token},body:JSON.stringify(data)};
  const response=await fetch(path,options); const result=await response.json();
  if(!response.ok) throw new Error(result.error||`请求失败 (${response.status})`);
  return result;
}
function currentProblem(){return app.problems.find(p=>p.id===app.selected);}
function progress(id){return app.state.progress[id]||{};}
function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function due(id){const p=progress(id);return p.mastery==='需要重做'||(p.review_at&&p.review_at<=today());}
function status(id){return app.state.statuses[`${id}:${app.language}`]||'未开始';}
function markdown(text){return text.trim().split('\n').map(line=>line.startsWith('## ')?`<h3>${esc(line.slice(3))}</h3>`:line.trim()?`<p>${esc(line)}</p>`:'').join('');}
function position(){const before=$('editor').value.slice(0,$('editor').selectionStart).split('\n');$('linePosition').textContent=`第 ${before.length} 行，第 ${before.at(-1).length+1} 列`;}
function renderProblemHeader(p){
  const id=p.id;
  $('readingHeader').innerHTML=`<div class="heading-row"><h2>${String(p.number).padStart(2,'0')}　${esc(p.title)}</h2><button id="bookmarkBtn" class="bookmark" aria-label="${progress(id).bookmark?'取消收藏':'收藏题目'}" title="收藏题目">${progress(id).bookmark?'★':'☆'}</button></div><p><span class="badge ${p.difficulty==='基础'?'easy':''}">${p.difficulty}</span>${esc(p.topic)} / ${status(id)}${progress(id).seen_answer?' / 已看解答':''}</p>`;
  $('bookmarkBtn').addEventListener('click',async()=>{try{await flushForms();app.state=await api('/api/progress',{id,changes:{bookmark:progress(id).bookmark?0:1}});renderList();if(app.mode==='algorithms'&&app.selected===id)renderProblemHeader(p);}catch(e){toast(e.message);}});
}

function renderList(){
  const search=$('search').value.trim().toLowerCase(),topic=$('topicFilter').value,filter=$('statusFilter').value;
  const all=app.mode==='algorithms'?app.problems:app.mode==='lessons'?app.lessons:app.knowledge;
  const list=all.filter(p=>(!search||`${p.title} ${p.topic||''} ${p.number||''}`.toLowerCase().includes(search))&&(app.mode!=='algorithms'||!topic||p.topic===topic)&&(app.mode!=='algorithms'||!filter||(filter==='待复习'?due(p.id):filter==='收藏'?progress(p.id).bookmark:status(p.id)===filter)));
  let previous='';
  $('problemList').innerHTML=list.map(p=>{
    const heading=app.mode==='algorithms'&&p.topic!==previous?`<h3 class="topic-heading">${esc(p.topic)}</h3>`:'';previous=p.topic;
    const st=app.mode==='algorithms'?status(p.id):app.mode==='knowledge'&&app.state.knowledge[p.id]?.answer?'已作答':'';
    return `${heading}<div role="listitem"><button class="problem-row ${p.id===app.selected?'active':''}" data-select="${p.id}" ${p.id===app.selected?'aria-current="true"':''}><span class="problem-number">${p.number?String(p.number).padStart(2,'0'):app.mode==='knowledge'?p.id.slice(1):''}</span><span class="problem-name">${esc(p.title)}${app.mode==='algorithms'?`<small>${p.difficulty}${due(p.id)?' / 待复习':''}${progress(p.id).bookmark?' / 收藏':''}</small>`:''}</span><span class="status-dot ${st==='已通过'?'passed':''}" aria-label="${st||'未开始'}">${st==='已通过'?'✓':st==='尝试中'?'◐':st==='已作答'?'✓':'○'}</span></button></div>`;
  }).join('')||'<p class="empty-list">没有匹配的内容。可以清空搜索或调整筛选。</p>';
  $('count').textContent=`${list.length} 项`;
  const solved=app.problems.filter(p=>status(p.id)==='已通过').length;
  $('progressText').textContent=`${solved} / ${app.problems.length} 已通过`;$('progressBar').max=app.problems.length;$('progressBar').value=solved;
  $('progressLanguage').textContent=app.language==='rust'?'Rust':'Python';
}

function rememberDraft(){
  const snapshot={id:app.selected,language:app.language,code:$('editor').value,updated_at:new Date().toISOString()};
  if(!storageSet(draftKey(snapshot.id,snapshot.language),snapshot)) $('saveState').textContent='浏览器备份不可用，等待本机保存';
  app.dirty=true;return snapshot;
}
function queueDraft(snapshot){
  const operation=app.saveChain.catch(()=>{}).then(async()=>{
    const result=await api('/api/draft',snapshot);
    const key=draftKey(snapshot.id,snapshot.language),local=storageGet(key);
    if(local&&local.code===snapshot.code&&local.updated_at===snapshot.updated_at) storageRemove(key);
    if(app.selected===snapshot.id&&app.language===snapshot.language&&$('editor').value===snapshot.code){app.dirty=false;$('saveState').textContent='已保存到本机';}
    return result;
  });
  app.saveChain=operation;
  operation.catch(error=>{if(app.selected===snapshot.id&&app.language===snapshot.language)$('saveState').textContent='保存失败，代码保留在浏览器';toast(error.message);});
  return operation;
}
async function flushDraft(){clearTimeout(saveTimer);if(app.mode==='algorithms'&&app.selected&&app.dirty)return queueDraft(rememberDraft());return app.saveChain;}
function changed(){const snapshot=rememberDraft();$('saveState').textContent='正在保存…';clearTimeout(saveTimer);saveTimer=setTimeout(()=>queueDraft(snapshot),600);position();}

async function select(id){
  try{await flushForms();await flushDraft();}catch(error){toast(`切换前保存失败：${error.message}`);return;}
  app.selected=id;app.epoch++;const epoch=app.epoch;storageSet('seagull:last',{mode:app.mode,id,language:app.language});
  renderList();
  if(app.mode==='algorithms'){
    const p=currentProblem();if(!p)return;
    $('editor').disabled=true;$('saveState').textContent='读取草稿…';$('results').innerHTML='<div class="empty-result"><h3>尚未运行</h3><p>运行示例或提交当前代码，查看反馈。</p></div>';
    try{
      const {draft}=await api(`/api/draft?id=${id}&language=${app.language}`);if(epoch!==app.epoch)return;
      const local=storageGet(draftKey(id,app.language));
      const newer=local&&(!draft||Date.parse(local.updated_at)>Date.parse(draft.updated_at));
      $('editor').value=newer?local.code:draft?.code??p.templates[app.language];app.dirty=!!newer;
      $('saveState').textContent=newer?'恢复了未同步草稿，正在保存…':'已保存到本机';
      if(newer)queueDraft(local);else if(local)storageRemove(draftKey(id,app.language));
      $('filename').textContent=app.language==='rust'?'solution.rs':'solution.py';position();
    }catch(error){$('saveState').textContent='草稿读取失败';toast(error.message);$('editor').value=p.templates[app.language];}
    finally{$('editor').disabled=false;}
  }
  await renderReading();
}

async function renderReading(){
  const id=app.selected,epoch=app.epoch;
  if(app.mode==='lessons'){
    const l=app.lessons.find(x=>x.id===id);if(!l)return;
    $('readingHeader').innerHTML=`<h2>${esc(l.title)}</h2><p>${esc(l.topic)} / 先理解适用条件，再记住实现方式</p>`;
    $('readingBody').innerHTML=markdown(l.body);return;
  }
  if(app.mode==='knowledge'){
    const k=app.knowledge.find(x=>x.id===id);if(!k)return;const record=app.state.knowledge[id]||{};
    $('readingHeader').innerHTML=`<h2>${esc(k.title)}</h2><p>后训练面试练习 / 开放题采用参考要点与自评</p>`;
    $('readingBody').innerHTML=`<p>${esc(k.question)}</p><div class="knowledge-form"><label for="knowledgeAnswer">先写出你的解释与例子</label><textarea id="knowledgeAnswer" placeholder="可以用：目标、公式含义、实现细节、边界与反例来组织回答。">${esc(record.answer||'')}</textarea><div id="knowledgeSave" class="form-state">${record.answer?'已保存到本机':'输入后自动保存'}</div><label for="knowledgeMastery">掌握程度</label><select id="knowledgeMastery">${app.mastery.map(x=>`<option ${record.mastery===x?'selected':''}>${x}</option>`).join('')}</select></div><details class="knowledge-points"><summary>展开参考要点，核对自己的回答</summary><ul>${k.points.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p class="subtle">这些要点用于复习，不是对开放回答的自动评分。</p></details>`;
    $('knowledgeAnswer').addEventListener('input',scheduleKnowledge);$('knowledgeMastery').addEventListener('change',scheduleKnowledge);return;
  }
  const p=currentProblem();if(!p)return;
  renderProblemHeader(p);
  document.querySelectorAll('.tab').forEach(b=>{b.classList.toggle('active',b.dataset.tab===app.tab);b.setAttribute('aria-selected',String(b.dataset.tab===app.tab));});
  if(app.tab==='problem'){
    $('readingBody').innerHTML=`<h3>任务</h3><p>${esc(p.description)}</p><h3>函数接口</h3><pre>${esc(p.templates[app.language].split('\n')[0])}</pre><p class="subtle">参数按接口顺序传入。请返回结果；无需编写输入解析或 main。</p>${p.examples.map((c,i)=>`<div class="example"><h4>示例 ${i+1}</h4><pre>${c.input.map((v,j)=>`${esc(p.args[j][0])} = ${esc(JSON.stringify(v))}`).join('\n')}\n返回结果：${esc(JSON.stringify(c.expected))}</pre></div>`).join('')}<div class="note-box">${p.test_count} 个测试用例。运行示例检查前两个，提交检查全部。${p.unordered?'本题外层答案顺序任意，仍需保持完整性且不能重复。':''}</div><button id="topicLesson" class="secondary">阅读「${esc(p.topic)}」背景知识</button>`;
    $('topicLesson').addEventListener('click',()=>{app.tab='lesson';renderReading();});
  }else if(app.tab==='lesson'){
    const lesson=app.lessons.find(l=>l.topic===p.topic);
    $('readingBody').innerHTML=`<div class="lesson-index"><button id="rustLesson">Rust 入门</button><button id="studyLesson">学习方法</button></div>${lesson?markdown(lesson.body):'<p>该专题内容正在补充。</p>'}`;
    $('rustLesson').addEventListener('click',()=>switchMode('lessons','rust'));$('studyLesson').addEventListener('click',()=>switchMode('lessons','start'));
  }else if(app.tab==='solution'){
    const n=app.hints[id]||0;
    $('readingBody').innerHTML=`<h3>先尝试，再展开</h3><p>用自己的话定义状态或不变量，写出一个能验证思路的小例子。</p><button id="hintBtn" class="secondary" ${n>=p.hints.length?'disabled':''}>${n>=p.hints.length?'提示已全部展开':`展开提示 ${n+1}`}</button>${p.hints.slice(0,n).map((h,i)=>`<div class="hint-box"><strong>提示 ${i+1}</strong><p>${esc(h)}</p></div>`).join('')}<h3>参考解答</h3><p class="subtle">展开会记录“已看解答”。通过状态与自评掌握程度分别保存。</p><button id="solutionBtn">展开 ${app.language==='rust'?'Rust':'Python'} 解答</button><div id="solutionContent"></div>`;
    $('hintBtn').addEventListener('click',()=>{app.hints[id]=n+1;renderReading();});
    $('solutionBtn').addEventListener('click',async()=>{
      try{const answer=await api('/api/solution',{id,language:app.language});if(epoch!==app.epoch||app.tab!=='solution')return;
        app.state.progress[id]={...progress(id),seen_answer:1};
        renderProblemHeader(p);
        $('solutionContent').innerHTML=`<h3>思路与正确性</h3><p>${esc(p.approach)}</p><h3>参考代码</h3><pre class="solution-code">${esc(answer.code)}</pre><h3>复杂度</h3><p>${esc(p.complexity)}</p><h3>常见错误</h3><p>${esc(p.pitfalls)}</p>`;
        $('solutionBtn').disabled=true;$('solutionBtn').textContent='已展开并记录';
      }catch(e){toast(e.message);}
    });
  }else if(app.tab==='history'){
    $('readingBody').innerHTML='<p class="subtle">读取提交记录…</p>';
    try{const {history}=await api(`/api/history?id=${id}&language=${app.language}`);if(epoch!==app.epoch||app.tab!=='history')return;
      $('readingBody').innerHTML=`<p class="subtle">显示当前语言最近 100 次运行与提交。完整记录包含在备份里。恢复代码不会删除提交历史。</p>${history.map((h,i)=>`<details class="history-item"><summary><span class="${h.result.status==='通过'?'pass-text':'fail-text'}">${esc(h.result.status)}</span><span class="subtle">${h.mode==='run'?'示例':'提交'} ${h.result.passed}/${h.result.total} / 题目 v${h.problem_version}</span><time>${new Date(h.created_at).toLocaleString('zh-CN',{hour12:false})}</time></summary><pre>${esc(h.code)}</pre><p class="subtle">${esc(h.result.message)}</p>${h.result.stderr?`<pre>${esc(h.result.stderr)}</pre>`:''}<button class="secondary" data-restore="${i}">恢复到编辑器</button></details>`).join('')||'<p>暂无运行记录。</p>'}`;
      if(!history.length)$('readingBody').innerHTML+='<p>运行示例或提交代码后，代码快照会自动保存。</p>';
      $('readingBody').querySelectorAll('[data-restore]').forEach(b=>b.addEventListener('click',()=>{
        if(!confirm('将历史代码恢复到编辑器？现有提交记录会保留。'))return;
        $('editor').value=history[Number(b.dataset.restore)].code;changed();toast('历史代码已恢复，正在保存草稿');
      }));
    }catch(e){$('readingBody').innerHTML=`<p>${esc(e.message)}</p>`;}
  }else if(app.tab==='review'){
    const r=progress(id);
    $('readingBody').innerHTML=`<h3>通过 ≠ 掌握</h3><p>记录完成方式，方便下次闭卷重做。自评和笔记属于题目，两种语言共享；编程通过状态分别保存。</p><div class="review-form"><label for="mastery">掌握程度</label><select id="mastery">${app.mastery.map(x=>`<option ${r.mastery===x?'selected':''}>${x}</option>`).join('')}</select><label for="reviewAt">下次复习日期</label><input id="reviewAt" type="date" value="${esc(r.review_at||'')}"><button id="reviewTomorrow" class="secondary">安排明天复习</button><label for="notes">笔记、疑问与反例</label><textarea id="notes" placeholder="例如：为什么容量要倒序？空数组会发生什么？">${esc(r.notes||'')}</textarea><div id="notesSave" class="form-state">输入后自动保存</div></div>`;
    for(const key of ['mastery','reviewAt','notes'])$(key).addEventListener(key==='notes'?'input':'change',scheduleNotes);
    $('reviewTomorrow').addEventListener('click',()=>{const d=new Date();d.setDate(d.getDate()+1);$('reviewAt').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;scheduleNotes();});
  }
}

let pendingNotes=null,pendingKnowledge=null;
function scheduleNotes(){pendingNotes={id:app.selected,changes:{mastery:$('mastery').value,notes:$('notes').value,review_at:$('reviewAt').value||null}};$('notesSave').textContent='正在保存…';clearTimeout(notesTimer);notesTimer=setTimeout(()=>saveNotes().catch(e=>toast(e.message)),600);}
async function saveNotes(){clearTimeout(notesTimer);const data=pendingNotes;if(!data)return;
  try{app.state=await api('/api/progress',data);if(pendingNotes===data)pendingNotes=null;if(app.selected===data.id&&$('notesSave'))$('notesSave').textContent='已保存到本机';renderList();}
  catch(e){if($('notesSave'))$('notesSave').textContent='保存失败，请保持页面打开重试';throw e;}}
function scheduleKnowledge(){pendingKnowledge={id:app.selected,answer:$('knowledgeAnswer').value,mastery:$('knowledgeMastery').value};storageSet(`seagull:knowledge:${app.selected}`,pendingKnowledge);$('knowledgeSave').textContent='正在保存…';clearTimeout(knowledgeTimer);knowledgeTimer=setTimeout(()=>saveKnowledge().catch(e=>toast(e.message)),600);}
async function saveKnowledge(){clearTimeout(knowledgeTimer);const data=pendingKnowledge;if(!data)return;
  try{await api('/api/knowledge',data);app.state.knowledge[data.id]=data;if(pendingKnowledge===data){pendingKnowledge=null;storageRemove(`seagull:knowledge:${data.id}`);}if(app.selected===data.id&&$('knowledgeSave'))$('knowledgeSave').textContent='已保存到本机';renderList();}
  catch(e){if($('knowledgeSave'))$('knowledgeSave').textContent='保存失败，回答保留在浏览器';throw e;}}
async function flushForms(){await saveNotes();await saveKnowledge();}
async function switchMode(mode,id){
  try{await flushForms();await flushDraft();}catch(e){toast(e.message);return;}
  app.mode=mode;app.selected=null;app.dirty=false;app.tab='problem';app.epoch++;
  $('workspace').classList.toggle('readonly',mode!=='algorithms');$('filters').hidden=mode!=='algorithms';$('progressWrap').hidden=mode!=='algorithms';$('tabs').hidden=mode!=='algorithms';
  $('listHeading').textContent=mode==='algorithms'?'练习路径':mode==='lessons'?'知识地图':'后训练问答';$('search').value='';
  document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  const all=mode==='algorithms'?app.problems:mode==='lessons'?app.lessons:app.knowledge;await select(all.some(x=>x.id===id)?id:all[0].id);
}

async function run(mode){
  if(app.busy||app.mode!=='algorithms'||$('editor').disabled)return;
  app.busy=true;const pid=app.selected,lang=app.language,epoch=app.epoch,code=$('editor').value;
  $('runBtn').disabled=$('submitBtn').disabled=true;$('language').disabled=true;$('resetBtn').disabled=true;
  $('results').innerHTML=`<p><span class="spinner"></span>${lang==='rust'?'正在编译 Rust，随后运行测试…':'正在运行测试…'}</p>`;
  try{await flushDraft();const response=await api('/api/judge',{id:pid,language:lang,code,mode});app.state=response.state;renderList();
    if(epoch!==app.epoch){toast(`「${app.problems.find(p=>p.id===pid).title}」${response.result.status}，已保存到提交记录`);return;}
    const r=response.result;
    renderProblemHeader(currentProblem());
    $('resultMeta').textContent=mode==='run'?'示例运行':'全部测试';
    const failures=r.cases.filter(c=>!c.passed),shown=failures.length?failures:r.cases.slice(0,2);
    $('results').innerHTML=`<div class="result-title"><strong class="${r.status==='通过'?'pass-text':'fail-text'}">${esc(r.status)}</strong><span>${r.passed} / ${r.total} 通过</span></div><p>${esc(r.message)}</p><p class="subtle">执行 ${r.execution_ms} ms${lang==='rust'?` / 编译 ${r.compile_ms} ms`:''}。耗时受本机与启动开销影响，仅供参考。</p>${r.stderr?`<details open><summary>${r.status==='编译错误'?'编译器信息':'异常信息'}</summary><pre>${esc(r.stderr)}</pre></details>`:''}${shown.map(c=>`<details ${!c.passed?'open':''}><summary>${c.passed?'✓':'×'} 用例 ${c.index}</summary><pre>输入：${esc(pretty(c.input))}\n期望：${esc(pretty(c.expected))}\n实际：${esc(pretty(c.actual))}</pre></details>`).join('')}${r.stdout?`<details><summary>调试输出</summary><pre>${esc(r.stdout)}</pre></details>`:''}`;
    if(app.tab==='history')await renderReading();
  }catch(e){if(epoch===app.epoch)$('results').innerHTML=`<strong class="fail-text">运行失败</strong><p>${esc(e.message)}</p>`;}
  finally{app.busy=false;$('runBtn').disabled=$('submitBtn').disabled=false;$('language').disabled=false;$('resetBtn').disabled=false;}
}

async function boot(){
  try{
    const data=await api('/api/bootstrap');Object.assign(app,data);app.language=storageGet('seagull:last')?.language==='rust'?'rust':'python';$('language').value=app.language;
    $('topicFilter').innerHTML='<option value="">全部专题</option>'+[...new Set(app.problems.map(p=>p.topic))].map(t=>`<option>${esc(t)}</option>`).join('');
    if(!data.environment.rust)toast('当前未找到 Rust 编译器，Python 可正常练习。');
    // Recover open-ended answers left in browser storage after an interrupted request.
    for(const k of app.knowledge){const local=storageGet(`seagull:knowledge:${k.id}`);if(local){await api('/api/knowledge',local);app.state.knowledge[k.id]=local;storageRemove(`seagull:knowledge:${k.id}`);}}
    const last=storageGet('seagull:last');await switchMode(['algorithms','lessons','knowledge'].includes(last?.mode)?last.mode:'algorithms',last?.id);
  }catch(e){$('bootError').hidden=false;$('bootError').textContent=`无法读取本地服务：${e.message}。确认 server.py 正在运行，再刷新页面。`;}
}

$('problemList').addEventListener('click',e=>{const b=e.target.closest('[data-select]');if(b)select(b.dataset.select);});
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>switchMode(b.dataset.mode)));
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',async()=>{try{await flushForms();app.tab=b.dataset.tab;await renderReading();}catch(e){toast(e.message);}}));
for(const key of ['search','topicFilter','statusFilter'])$(key).addEventListener(key==='search'?'input':'change',renderList);
$('language').addEventListener('change',async()=>{const next=$('language').value;$('language').value=app.language;try{await flushDraft();app.language=next;$('language').value=next;await select(app.selected);}catch(e){toast(e.message);}});
$('editor').addEventListener('input',changed);$('editor').addEventListener('click',position);$('editor').addEventListener('keyup',position);
$('editor').addEventListener('keydown',e=>{
  if(e.key==='Tab'){e.preventDefault();const t=e.target,start=t.selectionStart,end=t.selectionEnd;t.setRangeText('    ',start,end,'end');changed();}
  if(e.key==='Enter'&&e.ctrlKey){e.preventDefault();run('submit');}
  else if(e.key==='Enter'&&e.altKey){e.preventDefault();run('run');}
  else if(e.key==='Enter'&&!e.shiftKey&&!e.ctrlKey&&!e.metaKey){e.preventDefault();const t=e.target,prior=t.value.slice(0,t.selectionStart).split('\n').at(-1),indent=(prior.match(/^\s*/)||[''])[0]+(/[:{]\s*$/.test(prior)?'    ':'');t.setRangeText('\n'+indent,t.selectionStart,t.selectionEnd,'end');changed();}
});
$('resetBtn').addEventListener('click',()=>{if(confirm('将当前草稿重置为函数模板？提交历史会保留。')){$('editor').value=currentProblem().templates[app.language];changed();}});
$('runBtn').addEventListener('click',()=>run('run'));$('submitBtn').addEventListener('click',()=>run('submit'));
$('backupBtn').addEventListener('click',()=>$('backupDialog').showModal());$('helpBtn').addEventListener('click',()=>switchMode('lessons','start'));
$('exportBtn').addEventListener('click',async()=>{try{await flushForms();await flushDraft();const a=document.createElement('a');a.href='/api/export';a.download=`seagull-backup-${today()}.json`;document.body.append(a);a.click();a.remove();toast('已发起备份下载，请检查浏览器下载列表');}catch(e){toast(e.message);}});
$('importFile').addEventListener('change',async()=>{const file=$('importFile').files[0];if(!file)return;try{if(file.size>20000000)throw new Error('备份超过 20 MB，暂不支持导入');await flushForms();await flushDraft();const data=JSON.parse(await file.text()),r=await api('/api/import',data);app.state=await api('/api/state');$('importStatus').textContent=`已合并 ${r.imported} 条记录。原数据备份：${r.backup}`;await select(app.selected);}catch(e){$('importStatus').textContent=`导入失败：${e.message}`;}finally{$('importFile').value='';}});
window.addEventListener('beforeunload',e=>{if(app.dirty||pendingNotes||pendingKnowledge||app.busy){e.preventDefault();e.returnValue='';}});
window.addEventListener('pagehide',()=>{if(app.dirty&&app.mode==='algorithms')rememberDraft();});
boot();
