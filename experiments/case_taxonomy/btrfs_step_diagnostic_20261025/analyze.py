from pathlib import Path
import json,hashlib,sys,importlib.util,copy,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];PROJECT=ROOT/'linux_bug_analyze';sys.path.insert(0,str(PROJECT))
from linux_bug_analyze.btrfs_step_evidence import diagnostic_trace
from linux_bug_analyze.btrfs_watch_facts import project_watch_intervals,WatchEvidenceError
from linux_bug_analyze.btrfs_runtime_facts import project
spec=importlib.util.spec_from_file_location('obs',HERE.parent/'btrfs_consumer_observation_20261024/observations.py');obs=importlib.util.module_from_spec(spec);spec.loader.exec_module(obs)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in json.loads((HERE/'frozen_inputs.json').read_text()).items():assert sha(ROOT/p.replace('\\','/'))==h,p
cfg=json.loads((HERE/'prepared.json').read_text());runs=[];base_trace=None;base_events=None
baseline=json.loads((HERE.parent/'btrfs_fix_watch_20261025/verified_repeat.json').read_text())['facts']
for mode in ('default','explicit'):
 d=HERE/('runtime_'+mode);result=json.loads((HERE/('results_'+mode+'.json')).read_text())
 for filename,args in [('super.txt',['dump-super']),('tree.txt',['dump-tree','-t','5'])]:
  if not (d/filename).exists():(d/filename).write_bytes(subprocess.check_output(['btrfs','inspect-internal',*args,result['disk']]))
 facts=project(*[(d/n).read_text() for n in ('boot.log','super.txt','tree.txt')],requests=[2048,8192],sizes=[1024,6144,8192],context_id='step-diag-'+mode)
 events=obs.project_operands((d/'boot.log').read_text(),facts['fsid'],'step-diag-'+mode)
 trace=[json.loads(x) for x in (d/'rsp.jsonl').read_text().splitlines()]
 derived=diagnostic_trace(trace,mode,cfg['offsets']['max_inline'])
 intervals=project_watch_intervals(derived['trace'],cfg,events,context_id='step-diag-'+mode)
 assert {str(k):v for k,v in facts['effective_limits'].items()}==baseline['effective_limits']
 layout=lambda f:{(v['request'],v['size']):v['extent'] for v in f['files']}
 assert layout(facts)==layout(baseline)
 (d/'derived_trace.json').write_text(json.dumps(derived,indent=2)+'\n')
 runs.append(dict(mode=mode,intervals=intervals,step_diagnostics=derived['steps'],facts=facts,baseline_behavior_match=True,
   artifacts={n:sha(d/n) for n in ('boot.log','rsp.jsonl','super.txt','tree.txt','derived_trace.json')}))
 if mode=='default':base_trace=trace;base_events=events
controls=[]
for name in ('bad_mask','physical_mode','unchanged_pc','bad_store','wrong_object','wrong_state','wrong_store_value','unknown_packet','target_disarm','target_step_event'):
 trace=copy.deepcopy(base_trace)
 snap=next(i for i,x in enumerate(trace) if x['command'].startswith('z2,') and trace[i+1]['command']=='p0')
 step=next(i for i in range(snap,len(trace)) if trace[i]['command']=='s')
 if name=='bad_mask':trace[next(i for i,x in enumerate(trace) if x['command']=='qqemu.sstep')]['response']='0x1'
 elif name=='physical_mode':trace[next(i for i,x in enumerate(trace) if x['command']=='qqemu.PhyMemMode')]['response']='1'
 elif name=='unchanged_pc':trace[step+1]['response']=trace[snap+4]['response']
 elif name=='bad_store':trace[snap+6]['response']='00000000'
 elif name=='wrong_object':trace[snap+2]['response']='0100000000000000'
 elif name=='wrong_state':trace[step+6]['response']='00000000'
 elif name=='wrong_store_value':trace[step+8]['response']='0100000000000000'
 elif name=='unknown_packet':trace.insert(step,dict(command='qUnknown',response=''))
 elif name=='target_disarm':
  target=next(x['command'].replace('Z2','z2') for x in trace if x['command'].startswith('Z2,') and x['command'].endswith(',4'))
  trace.insert(step,dict(command=target,response='OK'))
 elif name=='target_step_event':trace[step]['response']='T05thread:01;watch:ffff0000008a9090;'
 try:
  derived=diagnostic_trace(trace,'default',cfg['offsets']['max_inline'])
  project_watch_intervals(derived['trace'],cfg,base_events,context_id='step-diag-default')
 except WatchEvidenceError as exc:controls.append(dict(name=name,rejected=True,reason=str(exc)))
 else:raise AssertionError('control accepted '+name)
result=dict(status='diagnostics_and_validation_complete',new_boots=2,new_intervals=4,new_positive_steps=8,runs=runs,controls=controls,
 anomaly_reproduced=False,root_cause='unresolved',historical_failure_reclassified=False,old_core_modified=False,model_calls=0,
 statement='Default queried 0x7; explicit set/readback also 0x7. Snapshot queries perturb timing; no causal attribution or reliability rate.')
(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],boots=2,steps=8,controls=len(controls),root_cause='unresolved')))
