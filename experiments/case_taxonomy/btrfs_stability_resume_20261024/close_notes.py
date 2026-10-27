"""Close a completed, reviewed model/material loop; preserve old pause records."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
paths=['btrfs_interval_stability','btrfs_interval_stability_supplement','btrfs_interval_stability_resumed']
rows=[]
for name in paths:
    p=ROOT/'模型调用测试/2026-10-24'/name/'receipt.json'
    r=json.loads(p.read_text(encoding='utf-8'))
    rows.append(dict(directory=name,receipt_sha256=sha(p),**{k:r.get(k) for k in ('status','elapsed_seconds','exit_code','stop_reasons','refusal_observed','visible_reported_tokens','conservative_accounted_tokens')}))
assert rows[-1]['status']=='complete_final_received' and rows[-1]['stop_reasons']==['end_turn']
assert not rows[-1]['refusal_observed']
assert (HERE/'scope_facts.json').exists()
total=sum(r['conservative_accounted_tokens'] for r in rows)
assert total<=1000000
result=dict(status='completed_limited_review',receipts=rows,cumulative_conservative_accounting=total,
    known_visible_tokens=sum(r['visible_reported_tokens'] or 0 for r in rows),total_usage_known=False,
    resumed_by_user=True,new_kernel_runs=0,core_modified=False,deadline='insufficient',whole_path='insufficient',
    rejected_model_admission='cache=4096 implies new-mount path',independent_positive=0,independent_normal=0)
save(HERE/'results.json',result)
before=json.loads((HERE/'notes_before.json').read_text(encoding='utf-8'))['before_sha256']
assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
    p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
    p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-24。用户已恢复实验；最新完成Btrfs补充源码分析和限定复核，消费期限仍不足。以下停点覆盖历史暂停状态。\n\n'+block+'\n\n以下为历史记录，按最新恢复状态解释。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-24.md').open('a',encoding='utf-8') as f:
    f.write('\n\n恢复前已补完暂停轮次三份文档同步，旧notes_sync.json为synced。\n'+block+'\n')
save(HERE/'notes_update.json',dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}))
print(json.dumps(dict(status=result['status'],conservative_accounting=total,notes=3)))
