"""Read-only replay of a fixed archive set; not a new-source detector."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,tempfile
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.btrfs_runtime_facts import project
from linux_bug_analyze.btrfs_watch_facts import project_watch_intervals,WatchEvidenceError
from linux_bug_analyze.btrfs_step_evidence import diagnostic_trace

def verify_file(path,digest):
 if not path.is_file():raise ValueError('missing registered artifact: '+str(path))
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('artifact SHA mismatch: '+str(path))

def selected(registry,requested):
 expected=['parent','fix','default','explicit']
 if [r['id'] for r in registry['runs']]!=expected:raise ValueError('incomplete or unknown registry')
 if requested!='all' and requested not in expected:raise ValueError('unregistered run')
 return registry['runs'] if requested=='all' else [r for r in registry['runs'] if r['id']==requested]

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',default='all');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 if args.output.exists():raise ValueError('preserve previous output; choose a new path')
 pins=json.loads((HERE/'frozen_inputs.json').read_text(encoding='utf-8'))
 for p,h in pins.items():verify_file(ROOT/p,h)
 registry=json.loads((HERE/'registry.json').read_text(encoding='utf-8'))
 runs=selected(registry,args.run)
 spec=importlib.util.spec_from_file_location('archived_operands',HERE.parent/'btrfs_consumer_observation_20261024/observations.py')
 obs=importlib.util.module_from_spec(spec);spec.loader.exec_module(obs)
 output=[];configs={};events_by_run={}
 for r in runs:
  cfg=json.loads((ROOT/r['prepared']).read_text(encoding='utf-8'));folder=ROOT/r['runtime'];context='closure-'+r['id']
  facts=project(*[(folder/n).read_text(encoding='utf-8') for n in ('boot.log','super.txt','tree.txt')],requests=[2048,8192],sizes=[1024,6144,8192],context_id=context)
  events=obs.project_operands((folder/'boot.log').read_text(encoding='utf-8'),facts['fsid'],context)
  raw=[json.loads(x) for x in (folder/'rsp.jsonl').read_text(encoding='utf-8').splitlines()]
  derived=diagnostic_trace(raw,r['diagnostic_mode'],cfg['offsets']['max_inline']) if r['diagnostic_mode'] else None
  intervals=project_watch_intervals(derived['trace'] if derived else raw,cfg,events,context_id=context)
  checks=[]
  for event,row in zip(events,intervals):
   checks.append(dict(interval_id=row['interval_id'],operand_event=event['event_id'],
     request=event['request'],cache=event['consumed_cache'],adjacent_disk=event['adjacent_disk_sample'],result=event['result'],
     arithmetic='satisfied' if event['result']==min(event['request'],event['consumed_cache']) else 'violated',
     cross_time_numeric_equality='satisfied' if row['cache']==row['disk_sample'] else 'violated',
     interval_evidence=row['interval_evidence'],relation_at_deadline='insufficient',whole_path='insufficient'))
  output.append(dict(run=r['id'],facts=facts,intervals=intervals,checks=checks,
      diagnostic_row_map=derived if derived else None))
  configs[r['id']]=cfg;events_by_run[r['id']]=events
 failure=dict(status='not_replayed_in_single_run_mode')
 if args.run=='all':
  for key in ('offsets','initrd_sha256','blank_sha256'):
   if any(c[key]!=configs['parent'][key] for c in configs.values()):raise ValueError('pairing mismatch: '+key)
  if configs['parent']['image_sha256']==configs['fix']['image_sha256']:raise ValueError('same parent/fix Image')
  if any(configs[x]['image_sha256']!=configs['fix']['image_sha256'] for x in ('default','explicit')):raise ValueError('diagnostic Image mismatch')
  raw=[json.loads(x) for x in (ROOT/registry['failed_trace']).read_text(encoding='utf-8').splitlines()]
  try:project_watch_intervals(raw,configs['fix'],events_by_run['fix'],context_id='closure-failed-fix')
  except WatchEvidenceError as exc:failure=dict(status='rejected',reason=str(exc),operand_context='successful fix events supplied only as parser expectation; failed attempt is not a completed observation')
  else:raise ValueError('incomplete attempt accepted')
  if failure['reason']!='single-step PC mismatch':raise ValueError('changed failure classification')
 controls=[]
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp)/'artifact';p.write_bytes(b'original');h=hashlib.sha256(p.read_bytes()).hexdigest();verify_file(p,h)
  for name in ('altered_artifact','missing_artifact','unknown_run','missing_registry_run'):
   try:
    if name=='altered_artifact':p.write_bytes(b'changed');verify_file(p,h)
    elif name=='missing_artifact':verify_file(Path(tmp)/'absent',h)
    elif name=='unknown_run':selected(registry,'unregistered')
    else:selected(dict(runs=registry['runs'][:-1]),'all')
   except ValueError as exc:controls.append(dict(name=name,rejected=True,reason=str(exc)))
   else:raise ValueError('boundary control accepted: '+name)
 checks=[c for r in output for c in r['checks']]
 result=dict(status='registered_archive_replay_complete',scope=registry['scope'],runs=output,failed_attempt=failure,controls=controls,
  summary=dict(replayed_runs=len(output),replayed_intervals=len(checks),replayed_file_records=sum(len(r['facts']['files']) for r in output),
   arithmetic_satisfied=sum(c['arithmetic']=='satisfied' for c in checks),cross_time_equal=sum(c['cross_time_numeric_equality']=='satisfied' for c in checks),cross_time_unequal=sum(c['cross_time_numeric_equality']=='violated' for c in checks),
   deadline_insufficient=len(checks),whole_path_insufficient=len(checks),new_boots=0,new_cases=0,model_calls=0,independent_positive=0,independent_normal=0),
  manual_dependencies=['archive selection and trusted hash registration','semantic diagnostic relations','known observation points and compiled offsets','configuration applicability and authoritative requirement review'],
  limitations=['hashes freeze currently available archive bytes, not independent authentication of historic collection','successful replay is not automatic requirement discovery','no global stability, alias, DMA, all-path or uninstrumented-equivalence proof'])
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result['summary']))

if __name__=='__main__':main()
