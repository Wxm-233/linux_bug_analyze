from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert not (HERE/'notes_update.json').exists(),'preserve receipt'
first=read(HERE/'delivery.json');last=read(HERE/'delivery_expanded.json')
assert first['finish_reasons']==['length'] and last['status']=='complete_final_received'
old=ROOT/'模型调用测试/2026-10-25/btrfs_kimi_helper_closure'
new=ROOT/'模型调用测试/2026-10-25/btrfs_kimi_helper_expanded'
assert sha(old/'prompt.md')==sha(new/'prompt.md')==read(HERE/'materials.json')['prompt_sha256']
a=read(old/'call_plan.json');b=read(new/'call_plan.json')
assert {k:v for k,v in a.items() if k!='max_output_tokens'}=={k:v for k,v in b.items() if k!='max_output_tokens'}
assert a['max_output_tokens']==24576 and b['max_output_tokens']==65536
assert read(HERE/'source_runtime_join.json')['counted_units']['replayed_intervals']==8
before=read(HERE/'notes_before.json')['before_sha256'];assert len(before)==3
for n,h in before.items():assert sha(ROOT/n)==h,n
block=(HERE/'conclusion.md').read_text(encoding='utf-8')
for n in before:
 p=ROOT/n;oldtext=p.read_text(encoding='utf-8-sig')
 p.write_text(oldtext.splitlines()[0]+'\n\n文档维护：2026-10-25。补齐校验/回调/调用边，核对父修复版本化运行；1次length及1次完整交付，C仍不足。\n\n'+block+'\n\n以下为历史记录，以最新状态为准。\n'+oldtext[oldtext.index('\n## '):],encoding='utf-8')
with (ROOT/'日志/2026-10-25.md').open('a',encoding='utf-8') as f:f.write('\n\n'+block+'\n')
(HERE/'notes_update.json').write_text(json.dumps(dict(before_sha256=before,after_sha256={n:sha(ROOT/n) for n in before}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(HERE/'results.json').write_text(json.dumps(dict(status='helper_evidence_reviewed_and_existing_runtime_joined',
 model_calls=2,complete_deliveries=1,length_truncations=1,new_kernel_runs=0,
 consumed_model_body='expanded complete only',deadline='insufficient',whole_path='insufficient',
 independent_positive=0,independent_normal=0,records={n:sha(HERE/n) for n in ('materials.json','delivery.json','delivery_expanded.json','source_review.md','source_runtime_join.json')}),indent=2)+'\n',encoding='utf-8')
print('Two calls preserved; scoped review, log and three notes updated; sync pending')
