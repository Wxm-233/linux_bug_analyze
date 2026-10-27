"""Apply unchanged frozen adapter to a successful fix and preserve failed trial."""
from pathlib import Path
import hashlib,json,sys,copy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
pins=json.loads((HERE/'frozen_inputs.json').read_text(encoding='utf-8'))
for p,h in pins.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.btrfs_watch_facts import project_watch_intervals,assess_interval_claim,WatchEvidenceError
rows={};cfgs={};events_by_mode={}
for mode,folder,runtime,verified in [('parent',HERE.parent/'btrfs_kernel_watch_20261025','runtime','verified.json'),('fix',HERE,'runtime_repeat','verified_repeat.json')]:
 cfg=json.loads((folder/'prepared.json').read_text());v=json.loads((folder/verified).read_text());assert v['status']=='verified'
 events=v['operand_events'];trace=[json.loads(x) for x in (folder/runtime/'rsp.jsonl').read_text().splitlines()]
 rows[mode]=project_watch_intervals(trace,cfg,events,context_id='paired-watch-'+mode)
 cfgs[mode]=cfg;events_by_mode[mode]=events
assert cfgs['parent']['offsets']==cfgs['fix']['offsets']
assert cfgs['parent']['initrd_sha256']==cfgs['fix']['initrd_sha256']
assert cfgs['parent']['blank_sha256']==cfgs['fix']['blank_sha256']
assert cfgs['parent']['image_sha256']!=cfgs['fix']['image_sha256']
first=[json.loads(x) for x in (HERE/'runtime/rsp.jsonl').read_text().splitlines()]
try:project_watch_intervals(first,cfgs['fix'],events_by_mode['fix'],context_id='failed-fix-attempt')
except WatchEvidenceError as exc:failure_reason=str(exc)
else:raise AssertionError('incomplete attempt accepted')
assert failure_reason=='single-step PC mismatch',failure_reason
pairs=[]
for p,f in zip(rows['parent'],rows['fix']):
 assert p['option']==f['option'] and p['disk_sample']==f['disk_sample']
 claim={k:f[k] for k in ('context_id','interval_id','object_id','operand_event','coverage','image_sha256','vmlinux_sha256')};claim['kind']='observed_no_target_write'
 good=assess_interval_claim(f,claim)
 assert good['interval_evidence']=='validated_no_target_write_record'
 wrong=copy.deepcopy(claim);wrong['image_sha256']=p['image_sha256']
 assert assess_interval_claim(f,wrong)['interval_evidence']=='insufficient'
 pairs.append(dict(option=p['option'],parent_cache=p['cache'],fix_cache=f['cache'],adjacent_disk=p['disk_sample'],
   parent_cache_equals_sample=p['cache']==p['disk_sample'],fix_cache_equals_sample=f['cache']==f['disk_sample'],
   parent_write_records=p['observed_target_writes'],fix_write_records=f['observed_target_writes'],
   parent_positive_after=[x['after'] for x in p['positive_events']],fix_positive_after=[x['after'] for x in f['positive_events']],
   relation_at_deadline='insufficient',whole_path='insufficient'))
result=dict(status='paired_limited_evidence',new_boot_attempts=2,new_complete_boots=1,new_failed_boots=1,
 new_complete_target_intervals=2,failed_attempt_adapter_rejection=failure_reason,
 pairing=pairs,projected=rows,method_hashes_unchanged=True,model_calls=0,
 independent_positives=0,independent_normals=0,collector_reliability='same-PC single-step stop once; not reproduced in one unchanged repeat; cause unresolved')
(HERE/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='projected'}))
