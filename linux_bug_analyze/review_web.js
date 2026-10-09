'use strict';
const token = location.hash.slice(1);
const el = id => document.getElementById(id);
let current = null, wasBusy = false, busy = false, refreshing = false, recordVersion = 0;
let summaryReturn = null;
async function api(path, values) {
  const response = await fetch(path, {method: values ? 'POST' : 'GET',
    headers: {'X-Review-Token': token, ...(values ? {'Content-Type': 'application/json'} : {})},
    ...(values ? {body: JSON.stringify(values)} : {})});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || response.statusText);
  return result;
}
function error(e) { el('error').textContent = e.message; }
async function action(name, values = {}) {
  busy = true;
  el('progress').textContent = '运行中 · 提交操作 ' + name;
  document.querySelectorAll('button').forEach(b => b.disabled = b.dataset.action !== 'stop');
  try {
    await api('/api/action', {action: name, ...values});
    wasBusy = true; busy = true;
    if (name === 'freeze' || name === 'sample') {
      el('role').value = name === 'freeze' ? 'validation' : 'audit';
      ++recordVersion;
      showRecord(null);
    }
    await refresh();
  }
  catch(e) { busy = false; document.querySelectorAll('button').forEach(b => b.disabled = false); error(e); }
}
function showRecord(r) {
  current = r;
  el('record').classList.toggle('hidden', !r);
  el('queue-hint').textContent = r ? '' : '当前队列没有待标注记录；可查看历史改判，或进入下一阶段。';
  if (!r) return;
  for (const k of ['subject', 'body', 'diff']) el(k).textContent = r[k];
  el('identity').textContent = `${r.hash} · ${r.date}`;
  el('files').textContent = r.files.join('\n');
  el('commit-link').href = r.url;
  el('note').value = '';
  const summary = r.reading_summary;
  el('reading-summary').textContent = summary ? `${summary.content.summary}\n\n${summary.content.limitations ? '局限：'+summary.content.limitations+'\n' : ''}${summary.material_truncated ? '注意：摘要输入材料已截断，完整 diff 仍可在下方查看。\n' : ''}\n证据：\n${summary.evidence.map(e=>'['+e.line+'] '+e.text).join('\n')}\n\n模型：${summary.model}` : '尚无摘要；请先批量生成当前队列摘要。';
}
async function next() {
  if (busy) return;
  const requestVersion = ++recordVersion;
  try { const r = await api('/api/next?role=' + el('role').value); if (requestVersion === recordVersion) showRecord(r); } catch(e) { error(e); }
}
async function loadRecord(hash) {
  const requestVersion = ++recordVersion;
  const r = await api('/api/material?hash=' + hash + '&role=' + el('role').value);
  if (requestVersion === recordVersion) showRecord(r);
}
function table(headers, rows) {
  const t = document.createElement('table');
  for (const [index, values] of [headers, ...rows].entries()) {
    const tr = document.createElement('tr');
    for (const value of values) { const td = document.createElement(index ? 'td' : 'th'); td.textContent = value; tr.append(td); }
    t.append(tr);
  } return t;
}
const names = {related:'LLM 相关', unrelated:'LLM 不相关', uncertain:'LLM 不确定', below_threshold:'低于阈值', regex_rejected:'正则未命中'};
async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    const r = await api('/api/status'), s = r.summary;
    busy = r.busy;
    el('progress').textContent = (busy ? '运行中 · ' : '') + r.progress;
    el('error').textContent = r.error || '';
    document.querySelectorAll('button').forEach(b => b.disabled = busy && b.dataset.action !== 'stop');
    el('role').disabled = busy;
    el('cards').replaceChildren();
    const labeled = Object.values(s.labels.train).reduce((a,b) => a+b, 0);
    for (const [title, number] of [['已扫描',s.dataset?.scanned || 0],['正则候选',s.dataset?.candidates || 0],['训练已读',labeled],['LLM 清单',s.selected ?? '未生成'],['待复核',s.audit_total ?? '未抽样']]) {
      const card = document.createElement('div'); card.className='card';
      const n = document.createElement('strong'); n.textContent=number; card.append(title,n); el('cards').append(card);
    }
    el('training-hint').textContent = `训练目标 ${s.training_target} 条；相关 ${s.labels.train.related} / 不相关 ${s.labels.train.unrelated} / 不确定 ${s.labels.train.uncertain}。${s.frozen ? '模型已冻结。' : '尚未冻结。'} 阈值检查 ${Object.values(s.labels.validation).reduce((a,b)=>a+b,0)}/${s.validation_total}。`;
    const llm = r.live_llm?.counts || s.llm;
    el('llm-status').textContent = `相关 ${llm.related} · 不相关 ${llm.unrelated} · 不确定 ${llm.uncertain}\n` +
      `未处理 ${r.live_llm?.unprocessed ?? s.llm.pending} · 调用/格式失败 ${r.live_llm?.failed ?? s.llm.failed}\n` +
      `模型 ${r.configured_model} · 累计请求 ${r.budget.requests || 0}/${r.budget.max_requests}\n` +
      `累计预算计费 token ${r.budget.charged_tokens || 0}/${r.budget.token_budget}（含未知用量预留）\n` +
      (r.live_llm?.status === 'stopped' ? '本轮已停止；请检查预算/接口状态后续跑。' : '');
    el('output').textContent = '结果目录：' + s.output_dir;
    el('reading-budget').textContent = `摘要独立累计预算：请求 ${r.reading_budget.requests || 0}/${r.reading_budget.max_requests}，token ${r.reading_budget.charged_tokens || 0}/${r.reading_budget.token_budget}。`;
    el('seed-search').classList.toggle('hidden', el('role').value !== 'train' || s.frozen);
    el('audit-stats').replaceChildren();
    if (s.audit) {
      const rows = Object.entries(s.audit.strata).map(([k,v]) => [names[k],v.population,v.sampled,v.reviewed,`${v.human_related}/${v.resolved}`,v.human_uncertain]);
      el('audit-stats').append(table(['分层','总体','抽样','已复核','人工相关/已确定','人工不确定'], rows));
      const p=document.createElement('p'); p.textContent='本轮加权二分类准确率：' + (s.audit.weighted_binary_accuracy === null ? '暂不估计（样本未全部解决或没有二分类结果）' : (s.audit.weighted_binary_accuracy*100).toFixed(1)+'%');
      el('audit-stats').append(p);
      const aid=document.createElement('p');aid.textContent=`其中 ${s.summary_assisted_labels.audit} 条已标注复核记录在标注前获得过 LLM 摘要。使用摘要的部分属于 LLM 辅助人工复核，不是完全独立盲审。`;el('audit-stats').append(aid);
    }
    const finished = wasBusy && !busy;
    wasBusy = busy;
    if (finished && summaryReturn) {
      const previous=summaryReturn; summaryReturn=null;
      if (previous.hash && previous.role===el('role').value) {
        await loadRecord(previous.hash); el('note').value=previous.note;
      } else if (s.dataset) await next();
    } else if (finished && !r.error && s.dataset) await next();
  } catch(e) { error(e); }
  finally { refreshing = false; }
}
document.querySelectorAll('[data-action]').forEach(b => b.onclick=()=>action(b.dataset.action));
document.querySelectorAll('[data-label]').forEach(b => b.onclick=async()=>{
  if (!current) return;
  await action('label', {hash:current.hash,role:el('role').value,label:b.dataset.label,note:el('note').value});
});
el('next').onclick=next;
el('summarize-queue').onclick=()=>{
  if (!confirm('将为当前人工审查队列批量生成事实摘要，使用独立摘要预算；已有缓存免费复用。确认调用模型？')) return;
  summaryReturn={hash:current?.hash,role:el('role').value,note:el('note').value};
  action('summarize_queue',{role:el('role').value,include_hash:current?.hash ?? null});
};
el('role').onchange=()=>{ el('history-results').replaceChildren(); el('search-results').replaceChildren(); showRecord(null); next(); refresh(); };
el('preview').onclick=async()=>{try{el('preview-result').textContent=JSON.stringify(await api('/api/preview?threshold='+encodeURIComponent(el('threshold').value)),null,2);}catch(e){error(e);}};
el('select').onclick=()=>{if(confirm('冻结后本轮不能修改阈值。确认使用当前阈值？'))action('select',{threshold:Number(el('threshold').value)});};
el('screen').onclick=()=>{if(!el('approve-api').checked)return error(new Error('请先勾选模型调用确认。')); action('screen');};
el('search').onclick=async()=>{try{
  el('search-results').replaceChildren();
  const rows=await api('/api/search?q='+encodeURIComponent(el('query').value));
  for(const row of rows){const b=document.createElement('button'); b.textContent=row.subject+' · '+row.hash.slice(0,12); b.onclick=async()=>{try{await loadRecord(row.hash);}catch(e){error(e);}};el('search-results').append(b);}
}catch(e){error(e);}};
el('history').onclick=async()=>{try{
  const rows=await api('/api/history?role='+el('role').value);
  const select=document.createElement('select');const empty=document.createElement('option');empty.textContent='选择历史记录以查看/改判';empty.value='';select.append(empty);
  for(const row of rows){const o=document.createElement('option');o.value=row.hash;o.textContent=row.hash.slice(0,12)+' · '+row.label;select.append(o);}
  select.onchange=async()=>{if(select.value){try{await loadRecord(select.value);if(current?.hash===select.value)el('note').value=rows.find(r=>r.hash===select.value).note;}catch(e){error(e);}}};
  el('history-results').replaceChildren(select);
}catch(e){error(e);}};
document.querySelectorAll('[data-download]').forEach(b=>b.onclick=async()=>{try{
  const response=await fetch('/api/download?name='+b.dataset.download,{headers:{'X-Review-Token':token}});
  if(!response.ok)throw new Error((await response.json()).error);
  const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=b.dataset.download;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}catch(e){error(e);}});
refresh(); setInterval(refresh,2500);
