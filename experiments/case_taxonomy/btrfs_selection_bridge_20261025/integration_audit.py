"""Labeled development mutations; never count as new profiles or cases."""
from pathlib import Path
import copy,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.contrast_selection import select_contrasts,profile_binding
from linux_bug_analyze.observation_planning import assess_observability
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in read(HERE/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
top=read(HERE.parent/'contrast_selection_20261017/example_pool.json')
by={p['id']:p for p in top['profiles']};original=[by['P01'],by['P03']]
rows=[]
for kind,reason in [('unknown_legality','legality_not_established'),('wrong_stage','build_or_adapter_not_established'),
 ('unverified_configuration','actual_configuration_not_verified'),('stale_review','profile_review_missing_or_mismatched')]:
 ps=copy.deepcopy(original);p=ps[0]
 if kind=='unknown_legality':p['legality']='unknown'
 if kind=='wrong_stage':p['availability']['adapter_stage']='after_consumer'
 if kind=='unverified_configuration':p['configuration']['verification']='config_only'
 if kind=='stale_review':p['cost']+=1
 else:p['review']['binding_sha256']=profile_binding(p)
 r=select_contrasts(top['contract'],ps,**top['options'])
 actual=next(x for x in r['profiles'] if x['id']=='P01')['reasons']
 assert not r['pairs'] and reason in actual
 rows.append(dict(control=kind,synthetic=True,expected_reason=reason,actual_reasons=actual,selected_pairs=0))
# Verify registered numeric assumptions, without deriving truth from a candidate.
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
manifest=read(raw/'manifest.json');sources=read(HERE.parent/'btrfs_helper_closure_20261025/source_runtime_join.json')['source']
assumptions=[]
for entry in manifest:
 mode=entry['mode'];disk=raw/mode/'super.txt';assert sha(disk)==entry['artifacts']['super.txt']
 geometry={key:int(re.findall(r'^'+key+r'\s+(\d+)$',disk.read_text(encoding='utf-8'),re.M)[0]) for key in ['sectorsize','num_devices']}
 assert geometry==dict(sectorsize=65536,num_devices=1)
 source=ROOT/sources[mode]['path'];assert sha(source)==sources[mode]['sha256']
 line=source.read_text(encoding='utf-8').splitlines()[sources[mode]['initial_line']-1]
 assert line.strip()=='fs_info->sectorsize = 4096;'
 assumptions.append(dict(mode=mode,geometry=geometry,initial_cache_source=line.strip(),source_sha256=sha(source),disk_sha256=sha(disk),
  assumption='4096 and 65536 are hypothetical alternatives, not proof of values at every deadline'))
gate=read(HERE/'observation_gate.json');available=copy.deepcopy(gate['available'])
available['disk_at_deadline']=dict(status='unknown',origin='reviewed_adapter',references=['adjacent_sample_is_not_reference'])
negative=assess_observability(gate['requirements']['full_candidate_observations'],available)
assert negative['missing']==['disk_at_deadline']
out=dict(synthetic_controls=rows,reference_substitution_control=negative,assumption_verification=assumptions,
 candidate_preserved=True,candidate_sha256=sha(HERE.parent/'btrfs_typed_model_20261025/ingested.json'),
 audit_scope='metadata rejection and bounded planner only; no new independent case or new runtime',
 unresolved=['normative authority','combined applicability','deadline citation mismatch','deadline reference','no admissible cross-architecture Btrfs pair in this two-profile pool'])
p=HERE/'integration_audit.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('4 labeled selector mutations rejected, reference substitution remains insufficient, numeric hypotheses source-checked')
