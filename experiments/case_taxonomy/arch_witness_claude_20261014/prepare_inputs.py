"""Focus an old interface, keeping outputs/oracle/runtime observations out."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'arch_witness_checks_20261014'
spec=importlib.util.spec_from_file_location('old_source_selection',OLD/'prepare_inputs.py')
source_selection=importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_selection)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def clip(doc,start,end):
    result=copy.deepcopy(doc)
    byline={int(line.split(':',1)[0]):line for line in doc['text'].splitlines()}
    assert all(n in byline for n in range(start,end+1))
    result.update(start_line=start,end_line=end,text='\n'.join(byline[n] for n in range(start,end+1)))
    return result


def main():
    if (HERE/'model_ledger.json').exists():raise RuntimeError('New requests already bound')
    old=json.loads((OLD/'requests/startup_pair.json').read_text())
    assert old['revision']=='88b604263f3d6eedae0b1c2c3bbd602d1e2e8775'
    docs={d['id']:copy.deepcopy(d) for d in old['documents']}
    # Keep the single-instance dispatch branch; the selected table is not multi-instance.
    docs['S_dispatch']=clip(docs['S_dispatch'],155,190)
    # Keep CPU identification, architecture preparation, and notify; unrelated APIC polling omitted.
    docs['S_x86_callin']=clip(docs['S_x86_callin'],186,214)
    docs['S_x86_callin_entry']=clip(next(d for d in old['documents'] if d['id']=='S_x86_callin'),162,165)
    docs['S_x86_callin_entry']['id']='S_x86_callin_entry'
    docs['S_x86_id']=clip(next(d for d in old['documents'] if d['id']=='S_x86_callin'),172,173)
    docs['S_x86_id']['id']='S_x86_id'
    # Include the common callin->online ordering, omitting unrelated trailing idle loop.
    docs['S_x86_start']=clip(docs['S_x86_start'],229,264)
    # The remaining map code handles package/core statistics, outside this target.
    docs['S_x86_prepare']=clip(docs['S_x86_prepare'],574,611)
    docs['S_s390_update']=clip(docs['S_s390_update'],251,271)
    for arch in ['x86','s390']:
        doc=docs['C_'+arch]
        doc['path']='../arch_witness_checks_20261014/'+doc['path']
    # Supply real surrounding configuration guards rather than infer them from names.
    docs['S_interface']=source_selection.document('startup','S_interface','include/linux/topology.h',197,208)
    docs['S_s390_header']=source_selection.document('startup','S_s390_header','arch/s390/include/asm/topology.h',27,33)
    docs['S_s390_guard']=source_selection.document('startup','S_s390_guard','arch/s390/include/asm/topology.h',11,12)
    # One top-level revision applies to every old source region; do not repeat it per region.
    for doc in docs.values():doc.pop('revision',None)
    common=['S_interface','S_notify','S_range','S_dispatch','S_table','S_starting','S_core','S_locks']
    pair=common+['S_x86_header','S_x86_callin_entry','S_x86_id','S_x86_callin','S_x86_start','S_x86_prepare','S_x86_link','C_x86',
        'S_s390_guard','S_s390_header','S_s390_start','S_s390_map','S_s390_update','C_s390']
    requests=[]
    for view,names in [('pair',pair),('ablated',common)]:
        id='startup_target_'+view
        value={'id':id,'unit':'startup_target','view':view,'revision':old['revision'],
            'target':{'interface':'cpu_smt_mask','consumer_phase':'CPUHP_AP_SCHED_STARTING -> sched_cpu_starting',
                'task':'从接口提供与共同首次消费原文提出适用检查，区分已有要求和证据不足。'},
            'scope_note':'Researcher selected an already-read interface. Old source only, with no fix/expected predicate/runtime labels.',
            'documents':[docs[name] for name in names]}
        p=HERE/'requests'/f'{id}.json';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        requests.append({'id':id,'relative_path':p.relative_to(HERE).as_posix(),'sha256':digest(p.read_bytes())})
    ledger=(OLD/'model_ledger.json').read_bytes();record=json.loads(ledger)
    accounted=sum(e['charged_tokens'] for e in record['entries'])
    assert accounted==52358 and record['stop_reason']=='usage_unknown_no_further_calls'
    manifest={'max_requests':2,'max_total_tokens':80000-accounted,'max_output_tokens':2000,
        'hidden_input_reserve_tokens':8192,'requests':requests,
        'carryover':{'ledger':'../arch_witness_checks_20261014/model_ledger.json','sha256':digest(ledger),
            'accounted_tokens':accounted,'overall_budget_tokens':80000}}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    receipt={'old_materials_used':'../arch_witness_checks_20261014/requests/startup_pair.json',
        'old_material_sha256':digest((OLD/'requests/startup_pair.json').read_bytes()),
        'new_raw_regions':source_selection.SOURCES,'changes':'Focused target; narrower dispatch/callin/secondary; configuration context retained.',
        'oracle_or_runtime_results_read':False,'external_calls':0}
    (HERE/'source_selection.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'prepared_requests':2,'remaining_budget':80000-accounted,'old_ledger_preserved':True}))


if __name__=='__main__':main()
