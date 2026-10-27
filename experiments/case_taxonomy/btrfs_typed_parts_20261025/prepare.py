from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not (HERE/'frozen_inputs.json').exists(),'preserve registration'
roles={}
for name,typ,category,meaning in [
 ('selected_profile','bool','configuration','Reviewed combined applicability; never alias for each configuration number.'),
 ('page_size','int','configuration','Page size in bytes, bound to the actual build/run.'),
 ('disk_sector_size','int','configuration','Decoded sectorsize of the registered filesystem archive; not a deadline observation.'),
 ('device_count','int','configuration','Registered filesystem device count.'),
 ('mount_flags','int','configuration','User syscall flags; cannot infer from a successful mount alone.'),
 ('request_values','int_set','configuration','Requests actually present in this registered run, not arbitrary future requests.'),
 ('cache','int','observation','Saved consumed cache operand.'),
 ('disk_at_deadline','int','observation','Applicable disk reference at consumption; absent unless separately evidenced.'),
 ('adjacent_disk','int','observation','Later disk sample, not interchangeable with deadline reference.'),
 ('request','int','observation','Saved requested value.'),
 ('result','int','observation','Saved clipped result.')]:
 roles[name]=dict(type=typ,role=category,meaning=meaning)
save('role_registry.json',roles)
save('protocol.json',dict(mode='development replay of previously read model candidate; not blind evaluation',
 candidate_edit_allowed=False,automatic_role_repair=False,
 split_rule='Flatten AND only; preserve OR/NOT and every original tree path.',
 unknown_reference_rule='Never supply disk_at_deadline from adjacent sample or config geometry.',
 role_registry_origin='researcher-authored typed interface vocabulary',
 expected_old_candidate_binding='remain insufficient; five configuration variables still alias selected_profile',
 local_results_are='diagnostic only; original scope failure prevents candidate admission',
 no_model_call=True,no_new_kernel_run=True))
files=[HERE/'role_registry.json',HERE/'protocol.json',HERE/'run.py',
 ROOT/'linux_bug_analyze/linux_bug_analyze/candidate_parts.py',ROOT/'linux_bug_analyze/tests/test_candidate_parts.py',
 ROOT/'模型调用测试/2026-10-25/btrfs_model_candidate/final.md',
 HERE.parent/'btrfs_model_candidate_20261025/documents.json',
 ROOT/'linux_bug_analyze/experiments/case_taxonomy/btrfs_consumer_observation_20261024/observations.py']
prior=json.loads((HERE.parent/'btrfs_model_candidate_20261025/frozen_inputs.json').read_text(encoding='utf-8'))
for p,h in prior.items():assert sha(ROOT/p)==h,p
prior.update({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files})
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
manifest=json.loads((raw/'manifest.json').read_text(encoding='utf-8'))[0]
for n in ('boot.log','super.txt','kernel.config'):
 assert sha(raw/'parent'/n)==manifest['artifacts'][n]
 prior[str((raw/'parent'/n).relative_to(ROOT)).replace('\\','/')]=sha(raw/'parent'/n)
save('frozen_inputs.json',prior)
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
shutil.copyfile(HERE.parent/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
print('Typed vocabulary, unchanged candidate and original evidence frozen for development replay')
