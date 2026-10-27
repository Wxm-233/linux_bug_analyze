"""Publish checked results with old-SHA guards; synchronization is separate."""
from pathlib import Path
import json
import hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

result=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
assert result['real_events']==4 and len(result['evaluations'])==12 and len(result['negative_controls'])==8
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8-sig'))['before_sha256']
assert len(before)==3
for name,h in before.items(): assert sha(ROOT/name)==h,name
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for name in before:
    path=ROOT/name
    old=path.read_text(encoding='utf-8-sig')
    title=old.splitlines()[0]
    history=old[old.index('\n## '):]
    path.write_text(title+'\n\n文档维护：2026-10-24。最新停点为Btrfs分层契约接线：4条既有事件完成12次评价，消费期限/完整路径仍不足。以下最新记录优先于历史停点。\n\n'+block+'\n\n以下为历史记录，按最新停点解释。\n'+history,encoding='utf-8')
with (ROOT/'日志/2026-10-24.md').open('a',encoding='utf-8') as f:
    f.write('\n\n'+block+'\n验证：冻结通用核心既有28项单元测试通过；新接线实际执行通过。WSL镜像同步待收据确认。\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Three Windows notes and daily log updated; mirror sync pending')
