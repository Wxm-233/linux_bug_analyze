from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
assert r['status']=='passed' and len(r['trace_negative_controls'])==11 and len(r['claim_negative_controls'])==8
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8-sig'))['before_sha256']
assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。最新完成内核区间证据适配器：2个旧区间通过、19项变异拒判；期限和全路径仍不足。\n\n'+block+'\n\n以下为历史记录，按最新停点解释。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Three notes and daily log updated; mirror sync pending')
