from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not (HERE/'frozen_inputs.json').exists(),'preserve registration'
base='linux_bug_analyze/experiments/case_taxonomy/'
runs=[]
for ident,folder,runtime,mode in [
 ('parent','btrfs_kernel_watch_20261025','runtime',None),
 ('fix','btrfs_fix_watch_20261025','runtime_repeat',None),
 ('default','btrfs_step_diagnostic_20261025','runtime_default','default'),
 ('explicit','btrfs_step_diagnostic_20261025','runtime_explicit','explicit')]:
 runs.append(dict(id=ident,prepared=base+folder+'/prepared.json',runtime=base+folder+'/'+runtime,diagnostic_mode=mode))
registry=dict(runs=runs,failed_trace=base+'btrfs_fix_watch_20261025/runtime/rsp.jsonl',
             scope='researcher_registered_archives_only',schema=1)
save('registry.json',registry)
paths={r['prepared'] for r in runs}
for r in runs:
 for n in ('boot.log','super.txt','tree.txt','rsp.jsonl'):paths.add(r['runtime']+'/'+n)
paths.add(registry['failed_trace'])
for n in ('btrfs_runtime_facts.py','btrfs_watch_facts.py','btrfs_step_evidence.py'):
 paths.add('linux_bug_analyze/linux_bug_analyze/'+n)
paths.add(base+'btrfs_consumer_observation_20261024/observations.py')
paths.update(str((HERE/n).relative_to(ROOT)).replace('\\','/') for n in ('registry.json','protocol_pre.md','run.py'))
save('frozen_inputs.json',{p:sha(ROOT/p) for p in sorted(paths)})
names=['当前代办.md','当前研究方向与进展.md','项目研究与文档写作交接说明.md']
save('notes_before.json',dict(before_sha256={n:sha(ROOT/n) for n in names}))
shutil.copyfile(HERE.parent/'new_input_contract_trial_20261017/sync_work_notes.py',HERE/'sync_work_notes.py')
print('Registered four archives, one failed trace, methods and three notes')
