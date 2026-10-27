"""Evidence failures and explicit synthetic counterexamples, no guest reruns."""
from pathlib import Path
import copy
import json

import contracts
import observer

HERE=Path(__file__).resolve().parent

def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

def main():
    observer.need(not (HERE/'controls.json').exists(),'preserve_original_controls')
    profiles={row['name']:row for row in observer.load(HERE/'boot_matrix.json')['profiles']}
    build=observer.load(HERE/'build_complete.json'); qualification=observer.load(HERE/'platform_qualification.json')
    traces={name:observer.collect(name) for name in ['baseline','nr2']}
    controls=[]
    def guard(name,profile,mutate):
        trace=copy.deepcopy(traces[profile]); b=copy.deepcopy(build); receipt=observer.load(HERE/'runs'/profile/'receipt.json')
        mutate(trace,b,receipt)
        try:
            observer.validate_trace(trace,profiles[profile],b,receipt,qualification)
        except (ValueError,KeyError) as exc:
            controls.append({'name':name,'kind':'constructed trace/identity control','expected':'insufficient','actual':'insufficient','reason':str(exc),'new_guest_boot':False})
            return
        raise ValueError('invalid_evidence_accepted:'+name)
    guard('different_kernel_release','baseline',lambda t,b,r:b.update(release='other_kernel'))
    guard('runtime_limit_argument_not_same_observation','nr2',lambda t,b,r:r.update(cmdline=r['cmdline'].replace('nr_cpus=2','nr_cpus=3')))
    guard('selected_CPU_mapping_observation_missing','baseline',lambda t,b,r:t['maps']['arch_after_prepare'].pop(16))
    def swap_stages(t,b,r):
        a=t['snapshots']['common_before_rebound']; z=t['snapshots']['common_after_rebound']; a['line'],z['line']=z['line'],a['line']
    guard('rebound_stage_order_swapped','baseline',swap_stages)
    guard('actual_secondary_register_read_missing','baseline',lambda t,b,r:t['hardware'].pop(16))
    guard('outside_runtime_domain_unknown_filled_as_false','nr2',lambda t,b,r:t['maps']['arch_after_prepare'][2].update(possible=0))
    items=observer.load(HERE/'analysis/arm64_contract_inputs.json')
    def get(kind,context='arm64.baseline'):
        return copy.deepcopy(next(i for i in items if i['kind']==kind and i['record']['context_id']==context))
    def synthetic(name,item,updates):
        item['record']['basis']=item['ledger']['basis']='synthetic'
        for key,value in updates.items():
            item['record']['facts'][key]['value']=value
            item['ledger']['claims']['fact.'+key]['fact']['value']=value
        facts={name:row['value'] for name,row in item['record']['facts'].items()}
        evidence=HERE/('control_'+name+'.json')
        save(evidence,{'constructed_control':True,'not_observed_kernel_state':True,'name':name,'facts':facts})
        document={'context_revision':item['contract']['revision'],'source_revision':item['contract']['revision'],
            'path':str(evidence.relative_to(contracts.INNER)),'sha256':contracts.sha(evidence),
            'start_line':1,'end_line':len(evidence.read_text(encoding='utf-8').splitlines())}
        item['ledger']['documents']['evidence']=document
        for claim in item['ledger']['claims'].values():
            claim['origin']='synthetic'; claim['statement']='Explicit constructed premise/control, not an observed kernel fact.'
            for ref in claim['references']:
                if ref['document']=='evidence': ref['end_line']=document['end_line']
        verdict=contracts.evaluate_contract(item['contract'],item['ledger'],item['record'],allow_synthetic=True)
        observer.need(verdict['relation_at_observation']=='violated',(name,verdict))
        controls.append({'name':name,'kind':'explicit synthetic counterexample','expected':'violated','actual':'violated','result':verdict,
                         'input':item,'new_guest_boot':False,'not_a_new_Linux_defect':True})
    # Applying SPARC's direct-identity adapter to actual ARM64 possible bits
    # would invent hardware ID16 and lose target256. This is an adapter error.
    raw_ids=set(traces['baseline']['provided_hardware'])
    direct=set(traces['baseline']['snapshots']['arch_after_prepare']['possible'])
    synthetic('wrong_direct_namespace_adapter_on_ARM64',get('mapping'),{'unprovided_hardware':sorted(direct-raw_ids)})
    synthetic('duplicate_selected_hardware_target',get('mapping'),{'unique_target_count':16})
    synthetic('actual_hardware_disagrees_with_mapping',get('hardware'),{'mismatched_online_hardware':[16]})
    before=traces['baseline']['snapshots']['common_before_rebound']['nr']
    synthetic('early_capacity_borrowed_as_late_runtime_bound',get('bound'),{'runtime_bound':before})
    max_trace=observer.collect('max2')
    synthetic('possible_count_borrowed_as_online_count',get('activation','arm64.max2'),
              {'online_count':len(max_trace['snapshots']['common_after_bringup']['possible'])})
    item=get('mapping'); item['ledger']['claims']['review.provider_binding']['status']='unknown'
    verdict=contracts.evaluate(item)
    observer.need(verdict['relation_at_observation']=='insufficient','unknown_provider_review_accepted')
    controls.append({'name':'all_local_facts_do_not_replace_provider_semantic_review','kind':'constructed review control',
                     'expected':'insufficient','actual':'insufficient','result':verdict,'new_guest_boot':False})
    save(HERE/'controls.json',{'rows':controls,'count':len(controls),'evidence_or_review_rejections':7,
        'explicit_synthetic_counterexamples':5,'all_expected_results':True,'new_core_evaluations':6,
        'new_guest_boots':0,'independent_samples':0})
    print(json.dumps({'controls':len(controls),'insufficient':7,'synthetic_violations':5,'new_guest_boots':0,'core_calls':6}))

if __name__=='__main__':
    main()
