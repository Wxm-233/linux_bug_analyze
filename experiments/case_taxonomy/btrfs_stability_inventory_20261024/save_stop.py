"""Record explicit user pause; no model invocation or research execution."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value): p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipts=[]
for name in ('btrfs_interval_stability','btrfs_interval_stability_supplement'):
    p=ROOT/'模型调用测试/2026-10-24'/name/'receipt.json'
    r=json.loads(p.read_text(encoding='utf-8'))
    assert r['status']!='started'
    receipts.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),
        **{k:r.get(k) for k in ('status','elapsed_seconds','exit_code','stop_reasons','refusal_observed','visible_reported_tokens','conservative_accounted_tokens','usage_known')}))
checkpoint=dict(status='paused_by_user',saved_at=datetime.now(timezone.utc).isoformat(),
    user_instruction='保存停点，先停下实验吧',active_model_process_stopped=True,
    supplemental_stop_reason='user_requested_termination_not_refusal_or_timeout',
    receipts=receipts,cli_tasks=2,conservative_accounted_tokens=sum(r['conservative_accounted_tokens'] for r in receipts),
    total_actual_usage='unknown',first_final='complete_but_only_partially_reviewed',
    supplemental_partial_used=False,new_kernel_runs=0,deadline_relation='insufficient',
    resume_requires_user_instruction=True,automatic_retry=False)
save(HERE/'checkpoint.json',checkpoint)
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8-sig'))['before_sha256']
assert len(before)==3
for n,h in before.items(): assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
    p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
    p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-24。用户已要求暂停实验；本轮补充Claude调用已终止，停点保存。未经用户恢复不继续。\n\n'+block+'\n\n以下为历史记录，服从最新暂停指示。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-24.md').open('a',encoding='utf-8') as f: f.write('\n\n'+block+'\n')
save(HERE/'notes_update.json',dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}))
print(json.dumps(dict(status='paused_by_user',cli_tasks=2,accounted=checkpoint['conservative_accounted_tokens'],notes=3)))
