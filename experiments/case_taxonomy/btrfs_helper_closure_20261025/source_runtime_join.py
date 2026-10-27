"""Join fixed source positions and re-extracted old runtime; no CFG proof."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=HERE.parent/'btrfs_stability_inventory_20261024'
source={}
for v in read(inventory/'inventory.json')['versions']:
 item=v['files']['fs/btrfs/disk-io.c'];p=inventory/item['artifact'];assert sha(p)==item['sha256']
 lines=p.read_text(encoding='utf-8').splitlines()
 initial=[i+1 for i,s in enumerate(lines) if re.fullmatch(r'\s*fs_info->sectorsize = 4096;',s)]
 cached=[i+1 for i,s in enumerate(lines) if re.fullmatch(r'\s*fs_info->sectorsize = sectorsize;',s)]
 calls=[i+1 for i,s in enumerate(lines) if re.fullmatch(r'\s*ret = btrfs_parse_options\(fs_info, options, sb->s_flags\);',s)]
 assert len(initial)==len(cached)==len(calls)==1
 source[v['mode']]=dict(revision=v['revision'],path=str(p.relative_to(ROOT)),sha256=sha(p),
  initial_line=initial[0],cache_assignment_line=cached[0],parse_call_line=calls[0],
  cache_assignment_lexically_before_parse=cached[0]<calls[0],
  excerpts=[dict(line=n,text=lines[n-1]) for n in initial+cached+calls])
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
builds={e['mode']:e for e in read(raw/'manifest.json')}
replay=read(HERE/'replayed_runtime.json');rows=[]
for run in replay['runs']:
 mode='parent' if run['run']=='parent' else 'fix'
 assert builds[mode]['revision']==source[mode]['revision']
 for interval,check in zip(run['intervals'],run['checks']):
  assert interval['interval_id']==check['interval_id']
  assert interval['image_sha256']==builds[mode]['image_sha256']
  rows.append(dict(run=run['run'],mode=mode,revision=source[mode]['revision'],image_sha256=interval['image_sha256'],
    interval_id=interval['interval_id'],request=check['request'],consumed_cache=check['cache'],
    adjacent_disk=check['adjacent_disk'],clipped_result=check['result'],
    lexical_assignment_before_parse=source[mode]['cache_assignment_lexically_before_parse'],
    deadline='insufficient',whole_path='insufficient'))
assert len(replay['runs'])==4 and len(rows)==8
assert sum(r['mode']=='parent' for r in rows)==2
assert all(r['consumed_cache']==(4096 if r['mode']=='parent' else 65536) and r['adjacent_disk']==65536 for r in rows)
assert not source['parent']['cache_assignment_lexically_before_parse'] and source['fix']['cache_assignment_lexically_before_parse']
result=dict(status='existing_source_runtime_join_verified',source=source,rows=rows,
 counted_units=dict(replayed_runs=4,replayed_intervals=8,parent_intervals=2,fix_intervals=6,new_boots=0),
 limitations=['lexical position is not CFG dominance or full effect proof','successful source-runtime linkage is not independent detection','parent and fixed builds must not be mixed','adjacent disk sample remains a distinct event'],
 replay_sha256=sha(HERE/'replayed_runtime.json'))
(HERE/'source_runtime_join.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Joined 4 old runs / 8 intervals: parent cache assignment after parse, fixed before; no deadline promotion')
