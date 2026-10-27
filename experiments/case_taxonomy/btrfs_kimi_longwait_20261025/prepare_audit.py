"""Audit existing materials and transport-only changes; never load credentials."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not (HERE/'prepared.json').exists(),'preserve preparation'
calls=ROOT/'模型调用测试/2026-10-25';new=calls/'btrfs_kimi_k3_longwait';old=calls/'btrfs_kimi_k3_newkey'
plan=read(new/'call_plan.json');prior=read(old/'call_plan.json')
assert {k:v for k,v in plan.items() if k!='wall_clock_seconds'}=={k:v for k,v in prior.items() if k!='wall_clock_seconds'}
assert plan['wall_clock_seconds']==1800 and prior['wall_clock_seconds']==600
assert sha(new/'prompt.md')==sha(old/'prompt.md')==plan['prompt_sha256']
materials=read(HERE.parent/'btrfs_path_closure_20261025/materials.json');docs=[]
for d in materials['documents']:
 p=Path(d['path']);assert sha(p)==d['sha256'],d['id']
 lines=p.read_text(encoding='utf-8').splitlines()
 for lo,hi in d['spans']:assert 1<=lo<=hi<=len(lines)
 docs.append(dict(id=d['id'],path=str(p),sha256=d['sha256'],spans=d['spans'],line_count=len(lines)))
save('prepared.json',dict(status='materials_and_plan_verified',documents=docs,
 prompt_sha256=plan['prompt_sha256'],same_wire_payload_expected=True,
 wall_clock_seconds=1800,socket_timeout_seconds=180,previous_socket_timeout_seconds=60,
 max_output_tokens=24576,per_call_allowance=1000000,old_receipt_sha256=sha(old/'receipt.json'),
 runner_sha256=sha(calls/'run_kimi_btrfs_longwait.py'),
 current_attempt=str(new.relative_to(ROOT)),default_route_changed=False))
shutil.copyfile(new/'notes_before.json',HERE/'notes_before.json')
shutil.copyfile(HERE.parent/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
print('14 original documents and exact prompt verified; only wall/socket wait limits changed')
