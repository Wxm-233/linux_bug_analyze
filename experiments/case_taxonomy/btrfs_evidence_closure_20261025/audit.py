"""Cross-check replay against prior receipts without rewriting them."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checked=[]
for name in ('btrfs_fix_watch_20261025','btrfs_step_diagnostic_20261025'):
 for p,h in read(HERE.parent/name/'frozen_inputs.json').items():
  assert sha(ROOT/p.replace('\\','/'))==h,p
  checked.append(p.replace('\\','/'))
old=read(HERE.parent/'btrfs_step_diagnostic_20261025/results.json')
for r in old['runs']:
 for p,h in r['artifacts'].items():assert sha(HERE.parent/'btrfs_step_diagnostic_20261025'/('runtime_'+r['mode'])/p)==h,p
new=read(HERE/'results.json');by={r['run']:r for r in new['runs']}
prior=[('parent',read(HERE.parent/'btrfs_kernel_watch_20261025/verified.json')['facts']),
       ('fix',read(HERE.parent/'btrfs_fix_watch_20261025/verified_repeat.json')['facts'])]
prior.extend((r['mode'],r['facts']) for r in old['runs'])
for name,facts in prior:
 actual=by[name]['facts']
 for key in ('fsid','page_size','sector_size','node_size','effective_limits'):assert actual[key]==facts[key],(name,key)
 shape=lambda f:sorted((v['request'],v['size'],v['extent'],v['persisted_equal']) for v in f['files'])
 assert shape(actual)==shape(facts),name
summary=new['summary']
assert (summary['replayed_runs'],summary['replayed_intervals'],summary['replayed_file_records'])==(4,8,24)
assert (summary['arithmetic_satisfied'],summary['cross_time_equal'],summary['cross_time_unequal'])==(8,6,2)
assert new['failed_attempt']['reason']=='single-step PC mismatch'
assert len(new['controls'])==4 and all(c['rejected'] for c in new['controls'])
assert all(c['relation_at_deadline']==c['whole_path']=='insufficient' for r in new['runs'] for c in r['checks'])
result=dict(status='verified',previous_pinned_paths_checked=sorted(set(checked)),
            prior_diagnostic_artifact_hashes_match=True,four_run_geometry_limits_layout_and_readback_match=True,
            deadline_promotions=0,results_sha256=sha(HERE/'results.json'))
(HERE/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Audit passed: previous pins, raw diagnostic hashes, four-run behavior, failure and scope preserved')
