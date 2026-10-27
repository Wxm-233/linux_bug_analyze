from pathlib import Path
import copy,hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.btrfs_watch_facts import project_watch_intervals,assess_interval_claim,WatchEvidenceError
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):(HERE/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pins=json.loads((HERE/'frozen_inputs.json').read_text(encoding='utf-8-sig'))
for p,h in pins.items():assert sha(ROOT/p)==h,p
old=HERE.parent/'btrfs_kernel_watch_20261025'
cfg=json.loads((old/'prepared.json').read_text(encoding='utf-8'))
trace=[json.loads(x) for x in (old/'runtime/rsp.jsonl').read_text(encoding='utf-8').splitlines()]
spec=importlib.util.spec_from_file_location('observer',HERE.parent/'btrfs_consumer_observation_20261024/observations.py')
observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
from linux_bug_analyze.btrfs_runtime_facts import project
facts=project(*[(old/'runtime'/n).read_text(encoding='utf-8') for n in ('boot.log','super.txt','tree.txt')],requests=[2048,8192],sizes=[1024,6144,8192],context_id='watch-adapter')
events=observer.project_operands((old/'runtime/boot.log').read_text(encoding='utf-8'),facts['fsid'],'watch-adapter')
rows=project_watch_intervals(trace,cfg,events,context_id='watch-adapter')
assert len(rows)==2 and rows[0]['info']==rows[1]['info'] and rows[0]['object_id']!=rows[1]['object_id']
claims=[];evaluations=[]
for row in rows:
 claim={k:row[k] for k in ('context_id','interval_id','object_id','operand_event','coverage','image_sha256','vmlinux_sha256')}
 claim['kind']='observed_no_target_write'
 claims.append(claim);evaluations.append(assess_interval_claim(row,claim))
assert all(x['interval_evidence']=='validated_no_target_write_record' and x['relation_at_deadline']==x['whole_path']=='insufficient' for x in evaluations)
controls=[]
for name in ('wrong_object','wrong_entry','wrong_return','wrong_stack','missing_install','failed_install','target_removed_during_step','missing_positive','target_write','wrong_thread','truncated'):
 t=copy.deepcopy(trace);ev=copy.deepcopy(events)
 first_watch=next(i for i,x in enumerate(t) if x['command']=='c' and 'watch:' in x['response'])
 target=f"{rows[0]['target_virtual_ranges'][0][0]:x}"
 install=next(i for i,x in enumerate(t) if x['command']==f'Z2,{target},4')
 if name=='wrong_object':ev[0]['info_pointer']='ffff000000000001'
 elif name=='wrong_entry':t[next(i for i,x in enumerate(t) if x['command']=='p20')]['response']='0100000000000000'
 elif name=='wrong_return':
  ret=rows[0]['return_pc'].to_bytes(8,'little').hex()
  i=next(i for i,x in enumerate(t) if x['command']=='p20' and x['response']==ret);t[i]['response']='0100000000000000'
 elif name=='wrong_stack':
  i=[i for i,x in enumerate(t) if x['command']=='p1f'][1];t[i]['response']='0100000000000000'
 elif name=='missing_install':del t[install]
 elif name=='failed_install':t[install]['response']='E01'
 elif name=='target_removed_during_step':
  i=next(i for i,x in enumerate(t) if x['command']=='s');t.insert(i,dict(command=f'z2,{target},4',response='OK'))
 elif name=='missing_positive':del t[first_watch:first_watch+8]
 elif name=='target_write':t[first_watch]['response']=f'T05thread:01;watch:{target};'
 elif name=='wrong_thread':t[first_watch]['response']=t[first_watch]['response'].replace('thread:01','thread:02')
 elif name=='truncated':t=t[:first_watch+5]
 try:project_watch_intervals(t,cfg,ev,context_id='watch-adapter')
 except WatchEvidenceError as exc:controls.append(dict(name=name,basis='synthetic_memory_mutation',rejected=True,reason=str(exc)))
 else:raise AssertionError('accepted '+name)
claim_controls=[]
for name in ('object_id','interval_id','operand_event','context_id','coverage','image_sha256','vmlinux_sha256','kind'):
 claim=copy.deepcopy(claims[0]);claim[name]='other' if name!='kind' else 'deadline_satisfied'
 result=assess_interval_claim(rows[0],claim)
 assert result['interval_evidence']==result['relation_at_deadline']=='insufficient'
 claim_controls.append(dict(name=name,result=result))
save('projected_intervals.json',rows);save('registered_claims.json',claims)
save('results.json',dict(status='passed',replayed_kernel_runs=1,replayed_intervals=2,evaluations=evaluations,
 trace_negative_controls=controls,claim_negative_controls=claim_controls,
 new_kernel_runs=0,model_calls=0,independent_positives=0,independent_normals=0,
 limitation='Strict archived collector protocol; trusted source identity and researcher scope required. No semantic or normative approval.'))
print('2 raw-trace intervals projected; 11 trace controls and 8 binding/promotion controls rejected; deadline stays insufficient')
