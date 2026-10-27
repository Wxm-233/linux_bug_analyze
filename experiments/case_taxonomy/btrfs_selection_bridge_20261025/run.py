from pathlib import Path
import copy,hashlib,importlib.util,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'linux_bug_analyze'))
from linux_bug_analyze.contrast_selection import SCHEMA,contract_binding,profile_binding,metadata_sha256,select_contrasts
from linux_bug_analyze.observation_planning import assess_observability,plan_clamp_probes
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 p=HERE/n;assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for p,h in read(HERE/'frozen_inputs.json').items():assert sha(ROOT/p)==h,p
raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024';manifest=read(raw/'manifest.json')
consumer=dict(interface='btrfs.geometry_before_max_inline',operation='min operand capture',stage='min_consumption',object_role='mounted_filesystem_geometry')
execution=dict(page_bytes=65536,disk_sector_bytes=65536,device_count=1,request_pool='2048,8192',mode='archived_initial_rw_mount')
contract=dict(schema=SCHEMA,id='btrfs_local_clamp_probe',purpose='max_inline_clipping_diagnostic',consumer=consumer,execution=execution,
 required_config={'CONFIG_ARM64_64K_PAGES':'y','CONFIG_BTRFS_FS':'y'},contrast_features=['cache_assignment_lexical_order'])
refs=['btrfs_selection_bridge_20261025/protocol.json','btrfs_helper_closure_20261025/source_runtime_join.json']
review=lambda binding:dict(status='reviewed',origin='researcher_review',binding_sha256=binding,references=refs)
contract['review']=review(contract_binding(contract));profiles=[]
sources=read(HERE.parent/'btrfs_helper_closure_20261025/source_runtime_join.json')['source']
for entry in manifest:
 mode=entry['mode'];cfg=HERE/(mode+'_config');header=HERE/(mode+'_autoconf.h')
 assert sha(cfg)==entry['artifacts']['kernel.config']
 cfgvalues=dict(re.findall(r'^(CONFIG_\w+)=(.+)$',cfg.read_text(encoding='utf-8'),re.M))
 macros=dict(re.findall(r'^#define (CONFIG_\w+) (.+)$',header.read_text(encoding='utf-8'),re.M))
 values={k:cfgvalues[k] for k in contract['required_config']}
 for k,v in values.items():assert v=='y' and macros[k]=='1'
 source=sources[mode];assert source['revision']==entry['revision'] and sha(ROOT/source['path'])==source['sha256']
 lines=(ROOT/source['path']).read_text(encoding='utf-8').splitlines()
 for excerpt in source['excerpts']:assert lines[excerpt['line']-1]==excerpt['text']
 order='before_parse' if source['cache_assignment_line']<source['parse_call_line'] else 'after_parse'
 profile=dict(id=mode,revision=entry['revision'],architecture='arm64',purpose=contract['purpose'],consumer=consumer,execution=execution,
  configuration=dict(sha256=sha(cfg),autoconf_sha256=sha(header),values=values,facts_sha256=metadata_sha256(values),verification='config_and_autoconf_verified'),
  availability=dict(build_status='archived_built',build_record_sha256=sha(raw/'manifest.json'),image_sha256=entry['image_sha256'],adapter='saved_clamp_operands',adapter_stage='min_consumption',references=refs),
  legality='legal',provider=dict(signature='btrfs cached geometry',features={'cache_assignment_lexical_order':order},references=refs),cost=1)
 profile['review']=review(profile_binding(profile));profiles.append(profile)
pool=dict(contract=contract,profiles=profiles,review_boundary='Assistant-reviewed narrow archived clipping diagnostic. Lexical order is not CFG dominance, readiness or permission to evaluate complete candidate.')
save('btrfs_pool.json',pool)
selection=select_contrasts(contract,profiles,max_pairs=1,max_cost=2,seed='btrfs-selection-20261025')
assert selection['status']=='insufficient'
assert {'different_revision','same_architecture'}<=set(selection['pair_decisions'][0]['reasons'])
save('btrfs_selection.json',selection)
candidate=read(HERE.parent/'btrfs_typed_model_20261025/ingested.json')
available={role:dict(status='available',origin='reviewed_adapter',references=['btrfs_consumer_observation_20261024/observations.py']) for role in ['cache','request','result','adjacent_disk']}
roles=sorted({candidate['candidate']['symbol_bindings'][s] for s,d in candidate['candidate']['contract']['symbols'].items() if d['role']=='observation'})
requirements=dict(full_candidate_observations=roles,clipping_diagnostic=['cache','request','result'])
gates={k:assess_observability(v,available) for k,v in requirements.items()}
assert gates['full_candidate_observations']['missing']==['disk_at_deadline']
assert not gates['clipping_diagnostic']['missing']
save('observation_gate.json',dict(requirements=requirements,available=available,results=gates,
 retained_candidate=candidate,other_unresolved=['selected_profile','semantic_authority','deadline_citation_matches_result_write'],
 full_contract_executable=False,formal_core_executions=0))
protocol=read(HERE/'protocol.json');probes=plan_clamp_probes(protocol['legal_requests'],protocol['source_hypotheses'])
save('probe_plan.json',probes)
# Re-run an existing supported development pool without modifying its inputs.
top=HERE.parent/'contrast_selection_20261017';tp=read(top/'example_pool.json')
tr=select_contrasts(tp['contract'],tp['profiles'],**tp['options'])
assert tr==read(top/'selection.json')
save('topology_regression.json',dict(selection=tr,identical_to_archived=True,new_case=False,new_migration=False))
# Runtime values are read only after saving the plans. Prior development exposure remains explicit.
spec=importlib.util.spec_from_file_location('operand_adapter',HERE.parent/'btrfs_consumer_observation_20261024/observations.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);events={}
for entry in manifest:
 mode=entry['mode'];folder=raw/mode
 for n in ['boot.log','super.txt']:assert sha(folder/n)==entry['artifacts'][n]
 disk=(folder/'super.txt').read_text(encoding='utf-8');fsid=re.findall(r'^fsid\s+([0-9a-f-]+)$',disk,re.M);assert len(fsid)==1
 boot=(folder/'boot.log').read_text(encoding='utf-8');events[mode]=mod.project_operands(boot,fsid[0],'selection-replay-'+mode)
 rows=[e for e in events[mode]]
 for e in rows:e['source_boot_sha256']=entry['artifacts']['boot.log']
replay=[]
for plan in probes['rows']:
 req=plan['request'];pair={m:next(e for e in es if e['request']==req) for m,es in events.items()}
 actual={m:e['result'] for m,e in pair.items()}
 replay.append(dict(request=req,planned_role=plan['role'],actual_results=actual,observed_difference=len(set(actual.values()))>1,events=pair,
  deadline_contract='insufficient',comparison_kind='historical_version_diagnostic_not_selected_cross_architecture_pair'))
assert [r['observed_difference'] for r in replay]==[False,True]
save('replay.json',dict(rows=replay,interpretation='hypothetical probe distinction agrees with known archival results; no independent effectiveness estimate',new_runs=0))
save('summary.json',dict(btrfs_selected_pairs=0,btrfs_pair_exclusions=selection['pair_decisions'][0]['reasons'],topology_selected_pairs=len(tr['pairs']),
 full_candidate_missing_observation=gates['full_candidate_observations']['missing'],diagnostic_probe_count=2,replayed_events=4,
 independent_positive=0,independent_normal=0,model_calls=0,new_boots=0))
print(json.dumps(read(HERE/'summary.json')))
