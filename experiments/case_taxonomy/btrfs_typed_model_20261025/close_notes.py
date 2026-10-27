from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert not (HERE/'notes_update.json').exists()
for p,h in read(HERE/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
r=read(HERE/'results.json');assert r['candidate_unchanged']
for row in r['rows']:
 d=row['diagnostics'];assert d['binding_status']=='typed_bindings_valid'
 assert d['summary']==dict(scope=dict(satisfied=5,violated=0,insufficient=2),relation=dict(satisfied=3,violated=0,insufficient=1))
before=read(HERE/'notes_before.json')['before_sha256'];assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
(HERE/'README.md').write_text('# 新类型词表候选接入实验\n\n'+block,encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。新模型候选类型通过、逐项接入旧事实；期限依据仍不足，下一步核对引用与事件语义。\n\n'+block+'\n\n以下为历史记录，以最新主线状态为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
artifacts=['results.json','ingested.json','intent_audit.json','audit_intent.py','conclusion.md']
(HERE/'output_manifest.json').write_text(json.dumps({n:sha(HERE/n) for n in artifacts},indent=2)+'\n',encoding='utf-8')
print('Updated three notes and daily log; WSL sync pending')
