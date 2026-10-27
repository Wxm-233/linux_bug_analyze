from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
assert r['status']=='passed' and [x['hits'] for x in r['runs']]==[3,3,0,0]
assert (HERE/'failure.json').exists() and (HERE/'environment.json').exists()
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8-sig'))['before_sha256']
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。最新完成QEMU写观察点合成能力验证；尚无Btrfs目标区间监控证据，消费期限仍不足。\n\n'+block+'\n\n以下为历史记录，按最新停点解释。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Three notes and daily log updated; mirror sync pending')
