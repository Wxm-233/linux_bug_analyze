from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert not (HERE/'notes_update.json').exists()
for p,h in read(HERE/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
before=read(HERE/'notes_before.json')['before_sha256']
for n,h in before.items():assert sha(ROOT/n)==h,n
assert len(read(HERE/'contrast_evidence.json')['rows'])==4
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
(HERE/'README.md').write_text(block,encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。事件引用错位已由程序识别，挂载flags已绑定；下一步将完整要求与观察限制接入有限对照选择。\n\n'+block+'\n以下为历史记录，以最新停点为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block)
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Updated log and three notes')
