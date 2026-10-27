from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
result=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
assert result['status']=='response_refused_no_semantic_adoption'
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。本轮补源已核，Claude主分析拒绝，未采纳正文；消费期限仍不足，累计保守记账965430。以下为最新停点。\n\n'+block+'\n\n以下为历史记录，按最新停点解释。\n'+old[old.index('\n## '):],encoding='utf-8')
log=ROOT/'日志/2026-10-25.md'
if not log.exists():log.write_text('# 2026年10月25日项目日志\n',encoding='utf-8')
with log.open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Three notes and daily log updated; mirror sync pending')
