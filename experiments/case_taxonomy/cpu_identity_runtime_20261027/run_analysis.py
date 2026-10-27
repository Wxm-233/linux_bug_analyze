"""Actual ARM64 observations plus old SPARC source-only adapter replay."""
from pathlib import Path
from collections import Counter
import json

import contracts
import observer

HERE=Path(__file__).resolve().parent

def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    out=HERE/'analysis'; out.mkdir(exist_ok=False)
    build=observer.load(HERE/'build_complete.json'); matrix=observer.load(HERE/'boot_matrix.json')
    inputs=[]; arm_rows=[]
    for profile in matrix['profiles']:
        name=profile['name']; trace=observer.collect(name); facts=observer.projections(trace)
        evidence=out/(name+'_observations.json')
        save(evidence,{'trace':trace,'program_facts':facts,'scope':'actual virtual OF/PSCI SMP normal-control development observations',
                       'physical_bare_metal_truth':False,'first_consumer_deadline_proved':False})
        decisions={}
        for kind,values in facts.items():
            item=contracts.envelope('arm64.'+name,build['revision'],'archived_runtime',kind,values,evidence)
            decision=contracts.evaluate(item); inputs.append(item); decisions[kind]=decision
        final=trace['snapshots']['common_after_bringup']; arch=trace['snapshots']['arch_after_prepare']
        maps=trace['maps']['arch_after_prepare']; selected=arch['possible']
        hardware_targets={maps[c]['hardware'] for c in selected if maps[c]['valid']}
        valid_slots={cpu for cpu,row in maps.items() if row['valid']}
        simplified={
            'possible_equals_raw_hardware_IDs':set(final['possible'])==set(trace['provided_hardware']),
            'all_selected_hardware_IDs_below_logical_bound':all(h<final['nr'] for h in hardware_targets),
            'every_valid_map_slot_must_be_possible':valid_slots<=set(selected),
            'present_must_equal_online':final['present']==final['online'],
            'runtime_bound_equals_compile_capacity':final['nr']==512}
        arm_rows.append({'profile':name,'possible':final['possible'],'present':final['present'],'online':final['online'],
            'nr_cpu_ids':final['nr'],'setup_max_cpus':final['max'],'NR_CPUS':512,
            'nr_before_rebound':trace['snapshots']['common_before_rebound']['nr'],
            'logical16_to_hardware':maps[16]['hardware'],'logical16_in_runtime_domain':maps[16]['domain'],
            'actual_online_hardware_records':len(trace['hardware']),
            'registered_count_hypothesis_matches':len(final['possible'])==profile['expected_possible_count'] and len(final['online'])==profile['expected_online_count'],
            'checks':decisions,'simplified_predicates_diagnostic_only':simplified})
    save(out/'arm64_contract_inputs.json',inputs)
    save(out/'arm64_results.json',{'rows':arm_rows,'new_core_evaluations':len(inputs),
        'contract_decision_counts':dict(Counter(d['relation_at_observation'] for row in arm_rows for d in row['checks'].values())),
        'not_independent_accuracy':True,'kernel_builds':1,'actual_new_guest_boots':4})
    # Old projection archive is read, not re-executed. Its unknown real boot
    # legality remains unknown. No old expected verdict is used for decisions.
    old=HERE.parent/'cpu_identity_contract_20261021'
    execution_path=old/'execution.json'; execution=observer.load(execution_path)
    old_result=observer.load(old/'results.json')
    observer.need(observer.sha(execution_path)==old_result['execution_sha256'],'legacy_execution_identity_changed')
    source_plan=observer.load(old/'source_plan.json')
    replay_inputs=[]; replay_rows=[]
    for run in execution['runs']:
        observer.need(run['returncode']==0 and run['status']=='returned','legacy_source_projection_incomplete')
        data=json.loads(run['stdout']); observer.need(data==run['observation'],'legacy_stdout_projection_disagrees')
        observer.need(data['NR_CPUS']==8 and data['BITS_PER_LONG']==64,'legacy_bitmap_scope_changed')
        bitmask=data['post_possible']; observer.need(type(bitmask) is int and 0<=bitmask<256,'legacy_bitmap_outside_scope')
        possible=[cpu for cpu in range(8) if bitmask&(1<<cpu)]
        provided=set(run['firmware_order'])
        mapping={'unprovided_hardware':sorted(set(possible)-provided),'missing_selected_map':[],
                 'selected_count':len(possible),'unique_target_count':len(possible)}
        selection={'selected_count':len(possible),'selection_limit':run['selection_limit']}
        evidence=out/(run['id']+'_source_projection.json')
        save(evidence,{'old_execution_sha256':observer.sha(execution_path),'id':run['id'],'version':run['version'],
            'firmware_order':run['firmware_order'],'original_observation':data,'possible':possible,
            'mapping_namespace':'provided SPARC cpuid is directly the bitmap index; identity mapping under old explicit substitutes',
            'new_boot':False,'real_configuration_legality':'unknown','program_facts':{'mapping':mapping,'selection':selection}})
        revision=source_plan['parent'] if run['version']=='parent' else source_plan['child']
        decisions={}
        for kind,values in [('mapping',mapping),('selection',selection)]:
            item=contracts.envelope('sparc_projection.'+run['id'],revision,'source_projection',kind,values,evidence,
                                    sample_stage='projected_after_setup_nr_cpu_ids')
            replay_inputs.append(item); decisions[kind]=contracts.evaluate(item)
        replay_rows.append({'id':run['id'],'version':run['version'],'possible':possible,'provided_hardware':sorted(provided),
            'mapping':decisions['mapping'],'selection':decisions['selection'],
            'old_count_equality_diagnostic':len(possible)==min(len(provided),run['selection_limit']),
            'evidence_tier':'old host source/API-substitute projection, no new execution'})
    save(out/'sparc_replay_inputs.json',replay_inputs)
    mapping_counts={version:dict(Counter(row['mapping']['relation_at_observation'] for row in replay_rows if row['version']==version)) for version in ['parent','fixed']}
    save(out/'sparc_replay_results.json',{'rows':replay_rows,'archive_core_replays':len(replay_inputs),
        'mapping_counts':mapping_counts,'selection_counts':dict(Counter(row['selection']['relation_at_observation'] for row in replay_rows)),
        'old_execution_sha256':observer.sha(execution_path),'new_executions':0,
        'same_mapping_relation_as_ARM64':True,'not_a_controlled_cross_architecture_boot_pair':True})
    save(out/'summary.json',{'new_ARM64_guest_boots':4,'new_kernel_builds':1,'new_PID1_builds':1,'new_model_calls':0,
        'new_ARM64_core_evaluations':len(inputs),'old_SPARC_record_replays':len(replay_rows),'old_SPARC_core_replays':len(replay_inputs),
        'ARM64_relation_counts':dict(Counter(d['relation_at_observation'] for row in arm_rows for d in row['checks'].values())),
        'SPARC_mapping_counts':mapping_counts,'independent_positive_normal':[0,0],
        'core_sha256':contracts.sha(contracts.CORE),'automatic_semantic_requirement_extractions':0,
        'source_policy_origin':'researcher reviewed, development data read before adapter/rule implementation'})
    print(json.dumps({'ARM64_profiles':[{k:row[k] for k in ['profile','nr_cpu_ids','possible','present','online','logical16_to_hardware']} for row in arm_rows],
                      'ARM64_core_checks':len(inputs),'SPARC_replay_mapping_counts':mapping_counts,'SPARC_core_replays':len(replay_inputs)}))

if __name__=='__main__':
    main()
