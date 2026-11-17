"""Join completed per-TU callback evidence by type; unknown targets stay open."""
from collections import Counter,defaultdict
from common import *
from prototype_batch import options,context
from prototype import compatible

def skey(signature):
    if signature is None:return None
    return json.dumps({k:signature[k] for k in ('result','arguments','variadic')},sort_keys=True)

def main():
    args=options();inputs,entries,root,build,out,digest=context(args)
    assert (out/'complete.txt').is_file(),'All batches must complete before summary'
    functions={};sites={};initializers={};assignments={};casts={};counts=Counter()
    for e in entries:
        p=out/'units'/f'{e["id"]:05d}.json.gz';row=read(p)
        assert row['status']=='ok' and row['input_digest']==digest
        m=row['macros'];cb=row['callbacks']
        counts['units']+=1;counts['macro_definitions_raw']+=len(m['definitions'])
        counts['macro_outer_regions_raw']+=len(m['outer_regions'])
        counts['macro_pending_regions_raw']+=sum(r['pending_region'] is not None for r in m['outer_regions'])
        for f in cb['functions']:functions[f['id']]=f
        for field,table in [('indirect_sites',sites),('initializers',initializers),('runtime_assignments',assignments),('casts',casts)]:
            for s in cb[field]:
                at=s.get('use',s.get('definition'))
                k=json.dumps([at,s.get('name'),s.get('object'),s.get('signature'),(s.get('owner') or {}).get('id')],sort_keys=True)
                r=table.setdefault(k,s|{'units':[]});r['units'].append(e['id'])
    typed=defaultdict(list);no_proto=defaultdict(list)
    signatures={}
    for ident,f in functions.items():
        sig=f['signature']
        if not sig:continue
        typed[skey(sig)].append(ident)
        signatures[skey(sig)]=sig
        if sig['arguments'] is None:no_proto[sig['result']].append(ident)
    groups={};group_ids={};site_rows=[]
    for site in sites.values():
        sig=site['signature'];k=skey(sig)
        if k not in group_ids:
            number=len(group_ids);group_ids[k]=number
            if sig is None:targets=sorted(functions)
            elif sig['arguments'] is None:
                targets=sorted(f['id'] for f in functions.values() if f['signature'] and f['signature']['result']==sig['result'])
            else:targets=sorted(set(typed.get(k,[]))|set(no_proto.get(sig['result'],[])))
            groups[number]={'id':number,'signature':sig,'possible_function_ids':targets,
                'complete_target_set':False,'unknown_region_policy':'Retain whole owner region for unscanned/extern/runtime/cast/ABI-dependent targets.'}
        site_rows.append(site|{'type_group':group_ids[k],'pending_region':site['region'],
                               'pending_reasons':['external_runtime_cast_and_ABI_targets_not_closed']})
    result={'summary':dict(counts)|{'function_entities':len(functions),'indirect_sites':len(site_rows),
                                 'type_groups':len(groups),'initializer_objects':len(initializers),
                                 'runtime_assignments':len(assignments),'function_pointer_casts':len(casts)},
            'functions':list(functions.values()),'type_groups':list(groups.values()),'indirect_sites':site_rows,
            'initializers':list(initializers.values()),'runtime_assignments':list(assignments.values()),'casts':list(casts.values()),
            'whole_program_complete':False,'input_digest':digest,
            'sample_match_or_boundary_pool_integration':False}
    with gzip.open(out/'callback_type_evidence.json.gz','wt',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,separators=(',',':'))
    (out/'summary.json').write_text(json.dumps(result['summary'],indent=2)+'\n')
    if args.fixture:
        assert result['summary']['indirect_sites']==4
        expected=read(HERE/'prototype_src/expected.json')
        funcs=functions
        for group in groups.values():
            got={funcs[i]['definition']['file']+':'+funcs[i]['name'] for i in group['possible_function_ids'] if funcs[i]['defined']}
            assert got==set(expected['callback_compatible_definitions']),got
        write('prototype_batch_selftest_result.json',{'passed':True,'output':str(out),'summary':result['summary'],
              'typed_callback_candidates_checked':True,'input_digest':digest})
    print(json.dumps(result['summary']),flush=True)

if __name__=='__main__':main()
