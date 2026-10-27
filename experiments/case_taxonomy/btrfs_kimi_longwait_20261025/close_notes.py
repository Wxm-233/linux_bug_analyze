from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert not (HERE/'notes_update.json').exists(),'preserve receipt'
d=read(HERE/'delivery.json');facts=read(HERE/'review_facts.json')
assert d['status']=='complete_final_received' and facts['config_claim']=='contradicted'
before=read(HERE/'notes_before.json')['before_sha256'];assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;old=p.read_text(encoding='utf-8-sig')
 p.write_text(old.splitlines()[0]+'\n\n文档维护：2026-10-25。Kimi完整交付并完成首轮复核；发现配置断言错误及消费/采样时刻混淆，C仍不足，下一步补具体函数效果。\n\n'+block+'\n\n以下为历史记录，以最新状态为准。\n'+old[old.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(HERE/'results.json').write_text(json.dumps(dict(status='complete_delivery_reviewed_no_deadline_promotion',
 model_calls=1,completed_deliveries=1,new_kernel_runs=0,new_independent_cases=0,
 config_claim='contradicted',deadline='insufficient',whole_path='insufficient',
 records={n:sha(HERE/n) for n in ('prepared.json','delivery.json','review_facts.json','source_review.md')}),indent=2)+'\n',encoding='utf-8')
print('Results, three notes and daily log updated; WSL sync pending')
