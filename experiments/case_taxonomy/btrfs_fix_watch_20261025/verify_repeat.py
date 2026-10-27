from pathlib import Path
import sys,json,subprocess,hashlib,importlib.util,copy
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];sys.path.insert(0,str(PROJECT))
from linux_bug_analyze.btrfs_runtime_facts import project
spec=importlib.util.spec_from_file_location('obs',HERE.parent/'btrfs_consumer_observation_20261024/observations.py');obs=importlib.util.module_from_spec(spec);spec.loader.exec_module(obs)
r=json.loads((HERE/'results_repeat.json').read_text());cfg=json.loads((HERE/'prepared.json').read_text());d=HERE/'runtime_repeat'
for name,args in [('super.txt',['dump-super']),('tree.txt',['dump-tree','-t','5'])]:
 p=d/name
 if not p.exists():p.write_bytes(subprocess.check_output(['btrfs','inspect-internal',*args,r['disk']]))
facts=project(*[(d/n).read_text() for n in ('boot.log','super.txt','tree.txt')],requests=[2048,8192],sizes=[1024,6144,8192],context_id='kernel-watch-fix')
events=obs.project_operands((d/'boot.log').read_text(),facts['fsid'],'kernel-watch-fix')
for row,event in zip(r['intervals'],events):
 assert int(event['info_pointer'],16)==row['info'] and int(event['super_pointer'],16)==row['super']
 assert event['consumed_cache']==row['cache'] and event['adjacent_disk_sample']==row['disk_before']==row['disk_after']
baseline=json.loads((HERE.parent/'btrfs_consumer_observation_20261024/results.json').read_text())['observations'][1]['facts']
assert {str(k):v for k,v in facts['effective_limits'].items()}==baseline['effective_limits']
layout=lambda f:{(v['request'],v['size']):v['extent'] for v in f['files']}
assert layout(facts)==layout(baseline)
trace=[json.loads(x) for x in (d/'rsp.jsonl').read_text().splitlines()]
row=r['intervals'][0];o=cfg['offsets']
targets={(row['super']+o['disk_sector'],4),(row['info']+o['super_pointer'],8)}
def audit(items):
 armed=set();steps=0;hits=0
 for item in items:
  cmd=item['command'];reply=item['response']
  if cmd.startswith(('Z2,','z2,')):
   assert reply=='OK'
   _,addr,length=cmd.split(',');key=(int(addr,16),int(length,16))
   if cmd[0]=='Z':armed.add(key)
   else:armed.remove(key)
  if cmd=='s' and targets & armed:
   assert targets<=armed,'target coverage gap during positive step'
   assert 'watch:' not in reply
   steps+=1
  if cmd=='c' and 'watch:' in reply:
   assert targets<=armed,'target not armed at positive hit'
   hits+=1
 assert hits==4 and steps==4,(hits,steps)
 return dict(positive_stops=hits,single_steps_with_both_targets_armed=steps)
audited=audit(trace)
bad=copy.deepcopy(trace);index=next(i for i,x in enumerate(bad) if x['command'].startswith('Z2,') and int(x['command'].split(',')[1],16)==row['super']+o['disk_sector'])
bad[index]['response']='E01'
try:audit(bad)
except AssertionError:control='rejected'
else:raise AssertionError('failed-installation control accepted')
out=dict(status='verified',facts=facts,operand_events=events,trace_audit=audited,failed_installation_control=control,
 baseline_behavior_match=True,artifacts={n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in ('boot.log','super.txt','tree.txt','rsp.jsonl')},
 limitation='Trace proves debugger commands and selected virtual-address coverage only; not aliases/DMA/all execution equivalence')
(HERE/'verified_repeat.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(status='verified',files=len(facts['files']),audit=audited)))
