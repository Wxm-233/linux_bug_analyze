from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert not (HERE/'notes_update.json').exists(),'preserve receipt'
r=read(HERE/'results.json');assert r['candidate_unchanged'] and r['distinct_relation_parts']==5
for p,h in read(HERE/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
before=read(HERE/'notes_before.json')['before_sha256'];assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。新增类型角色与复合候选完整分解，接真实事实；旧映射不修复，下一步新模型候选检验。\n\n'+block+'\n\n以下为历史记录，以最新主线状态为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Typed candidate progress and next model-input step recorded; WSL sync pending')
