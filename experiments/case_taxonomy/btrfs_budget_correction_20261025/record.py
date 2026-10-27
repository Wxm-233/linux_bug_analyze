"""Correct per-call accounting and audit existing input, without model execution."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not (HERE/'results.json').exists(),'preserve record'
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
folder=HERE.parent/'btrfs_path_closure_20261025'
materials=read(folder/'materials.json');calls=ROOT/'模型调用测试/2026-10-25/btrfs_actual_path_closure'
for d in materials['documents']:
 p=Path(d['path']);assert sha(p)==d['sha256']
 lines=p.read_text(encoding='utf-8').splitlines()
 for lo,hi in d['spans']:assert 1<=lo<=hi<=len(lines)
assert sha(calls/'prompt.md')==materials['prompt_sha256']
receipt=read(calls/'receipt.json');plan=read(calls/'call_plan.json')
assert receipt['status']=='response_refused' and receipt['refusal_observed']
assert plan['prompt_sha256']==materials['prompt_sha256']
policy=dict(user_clarified_date='2026-10-25',scope='per_new_call',token_allowance=1000000,
 historical_usage_deducted=False,aggregate_cap=None,historical_actual_usage_known=False,
 historical_conservative_total=965430,historical_total_is_not_actual_bill=True,
 withdrawn_remaining_allowance=34570,refusal_policy_unchanged=True,
 note='Authorization/accounting allowance, not a guarantee or configuration of client/model context or output limits.')
save('budget_policy.json',policy)
save('results.json',dict(status='budget_corrected_materials_verified_no_call',documents_verified=len(materials['documents']),
 prompt_sha256=materials['prompt_sha256'],receipt_sha256=sha(calls/'receipt.json'),
 original_receipt_preserved=True,refused_body_read=False,model_calls=0,new_kernel_runs=0,
 historical_prepare_has_obsolete_cumulative_guard=True,
 obsolete_guard_action='preserve historical prepare.py; do not reuse its cumulative-budget admission rule',
 shared_runner_has_no_cumulative_admission_guard=True,
 execution_state='awaiting_explicit_refusal_stop_override; budget is not a blocker',
 authoritative_budget_policy='budget_policy.json',deadline='insufficient',whole_path='insufficient'))
shutil.copyfile(HERE.parent/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
print('Budget policy corrected; 14 existing documents and exact prompt hash verified; no call')
