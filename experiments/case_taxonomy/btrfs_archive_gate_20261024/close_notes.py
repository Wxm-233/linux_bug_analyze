"""Publish completed archive checks with old-SHA guards."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

result=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
assert len(result['evaluations'])==12 and len(result['negative_controls'])==10
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8-sig'))['before_sha256']
assert len(before)==3
for n,h in before.items(): assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for name in before:
    p=ROOT/name;old=p.read_text(encoding='utf-8-sig')
    p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-24。最新完成Btrfs归档原件门禁，0次模型调用；消费期限稳定性仍待源码证据。以下最新停点优先于历史记录。\n\n'+block+'\n\n以下为历史记录，按最新停点解释。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-24.md').open('a',encoding='utf-8') as f: f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Three notes and daily log updated; WSL sync pending')
