from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'notes_update.json').exists(),'preserve receipt'
r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。用户授权Kimi-K3对照及新密钥调用；实际交付状态见最新章节，未自动提升Btrfs契约结论。\n\n'+block+'\n\n以下为历史记录，以最新用户指示和实测结果为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Daily log and three notes updated; WSL mirror pending')
