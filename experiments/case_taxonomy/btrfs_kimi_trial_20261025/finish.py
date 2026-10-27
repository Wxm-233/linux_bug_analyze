"""Record user-authorized Kimi trials; never read or copy credentials."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
old=ROOT/'模型调用测试/2026-10-25/btrfs_kimi_k3'
new=ROOT/'模型调用测试/2026-10-25/btrfs_kimi_k3_newkey'
original=ROOT/'模型调用测试/2026-10-25/btrfs_actual_path_closure_authorized_retry/prompt.md'
a=read(old/'receipt.json');b=read(new/'receipt.json')
assert b['status']!='started','await completed delivery'
assert a['error']['status']==401
assert sha(old/'prompt.md')==sha(new/'prompt.md')==sha(original)
assert a['model']==b['model']=='Kimi-K3' and b['default_route_changed']==False
assert not (HERE/'results.json').exists(),'preserve results'
save('results.json',dict(status=b['status'],model='Kimi-K3',protocol=b['protocol'],
 user_authorized_model_override=True,new_credential_external=True,default_route_changed=False,
 prompt_unchanged=True,prompt_sha256=sha(original),old_attempt_http_status=401,
 new_attempt={k:b.get(k) for k in ('status','elapsed_seconds','actual_models','finish_reasons','done_marker','network_eof','visible_reported_tokens','usage_known','final_characters','semantic_review_allowed','error')},
 receipt_hashes={'old':sha(old/'receipt.json'),'new':sha(new/'receipt.json')},
 new_model_attempts=2,new_kernel_runs=0,per_call_allowance=1000000,historical_usage_deducted=False,
 independent_positive=0,independent_normal=0))
shutil.copyfile(new/'notes_before.json',HERE/'notes_before.json')
shutil.copyfile(HERE.parent/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
print(json.dumps(read(HERE/'results.json'),ensure_ascii=True))
