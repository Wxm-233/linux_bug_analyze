"""Bounded, checkpointed remerge of existing caches. Never calls scan/parse_unit.

All checkpoints and outputs are under this audit round, not under old caches.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import pickle
import sys

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'boundary_enum_20261106'
sys.path.insert(0,str(OLD))
import enumerate as e
import merge_staged as frozen_merge
import repair_policy as policy

def collect_bindings(build):
    paths=e.Paths(build.source,build.output)
    archive=set(e.command(['llvm-ar','t','vmlinux.a'],cwd=build.output).splitlines())
    providers=defaultdict(set);final=defaultdict(set)
    for obj,name,code in e.read_nm(sorted(archive),build.output):
        if code in e.STRONG_NM|e.WEAK_NM:providers[name].add((obj,code))
    for _,name,code in e.read_nm(['vmlinux'],build.output):final[name].add(code)
    sources={str(en.output.relative_to(build.output)):paths.name(str(en.source)) for en in build.entries}
    return policy.binding_table(providers,final,sources)

def initialize(build):
    state=frozen_merge.initialize(build)
    state.update(bindings=collect_bindings(build),asm_points={},asm_resolved_refs=0)
    return state

def advance(build,state,limit):
    entries=[en for en in build.entries if en.is_c]
    paths=e.Paths(build.source,build.output)
    for entry,result in e.unit_records(build,entries[state['offset']:state['offset']+limit]):
        obj=str(entry.output.relative_to(build.output));linked=obj in state['archive']
        unit={'id':entry.number,'source':paths.name(str(entry.source)),'object':obj,'status':result['status'],
              'severity_counts':result.get('severity_counts'),'diagnostics':result.get('diagnostics',[]),'unresolved':None}
        state['units'].append(unit)
        if result['status']=='ok':
            local=[e.Symbol.from_row(row) for row in result['symbols']]
            resolved={};counts=Counter(result['unresolved']);examples=list(result['unresolved_examples'])
            state['visible_macros']+=result['visible_macros'];state['indirect_calls']+=result['indirect_calls']
            for at,action,number,owner in result['refs']:
                at=(sys.intern(at[0]),at[1],at[2]);symbol=local[number]
                if number not in resolved:
                    resolved[number]=policy.resolve_c(symbol,linked,state['definitions'],state['by_object'],
                        state['objects']['weak_overrides'],state['bindings'],e.resolve)
                target,reason=resolved[number]
                if target is None:
                    provider=policy.asm_provider(symbol,linked,state['bindings'])
                    if provider is not None:
                        key=(at,action,symbol,provider['object'])
                        row=state['asm_points'].setdefault(key,{'use':e.location_json(at),'action':action,
                            'declaration':e.symbol_json(symbol),'definition':provider|{'line':None,'column':None},
                            'direction':e.direction(at[0],provider['source']),'units':[],
                            'caller':e.symbol_json(local[owner]) if owner is not None else None})
                        if not row['units'] or row['units'][-1]!=entry.number:row['units'].append(entry.number)
                        state['asm_resolved_refs']+=1
                        continue
                    counts[reason]+=1
                    if len(examples)<20:examples.append([reason,symbol.name,at])
                    continue
                if owner is not None:state['calls'].setdefault((local[owner],target),(at,entry.number))
                cross=e.direction(at[0],target.at[0])
                if cross is not None:state['points'].add(at,action,target,cross,entry.number)
            unit.update(unresolved=dict(counts),unresolved_examples=examples,
                visible_macros=result['visible_macros'],indirect_calls=result['indirect_calls'])
            state['missing'].update(counts);state['missing_units']+=bool(counts)
        state['offset']+=1
        if state['offset']%64==0:print(f'{build.arch}: references {state["offset"]}/{len(entries)}',flush=True)
    return state['offset']==len(entries)

def finalize(build,state,output):
    output.mkdir(parents=True,exist_ok=True)
    summary=frozen_merge.finalize(build,state,output)
    runtime=e.BoundaryPoints();excluded=Counter();sources={u['id']:u['source'] for u in state['units']}
    symbols=list(state['points'].symbol_ids)
    for (at,action,number),units in state['points'].points.items():
        symbol,cross=symbols[number]
        allowed=[u for u in units if policy.runtime_point(at[0],[sources[u]])]
        if not allowed:excluded['points']+=1;continue
        for u in allowed:runtime.add(at,action,symbol,cross,u)
    # BoundaryPoints.emit names outputs by its arch argument, keeping raw outputs alongside them.
    runtime_summary=runtime.emit(output,'runtime_'+build.arch)
    asm_rows=list(state['asm_points'].values())
    e.save_lines(output/f'c_to_asm_{build.arch}.jsonl.gz',asm_rows)
    e.save_json(output/f'link_bindings_{build.arch}.json.gz',state['bindings'])
    summary.update(audit_revision={'criteria_sha256':e.sha256(HERE/'criteria.md'),
        'amendment2_sha256':e.sha256(HERE/'criteria_amendment2.md'),
        'repair_policy_sha256':e.sha256(HERE/'repair_policy.py'),'remerge_sha256':e.sha256(Path(__file__)),
        'runtime':runtime_summary,'runtime_excluded_points':excluded['points'],
        'c_to_asm_use_points':len(asm_rows),'c_to_asm_cross_points':sum(r['direction'] is not None for r in asm_rows),
        'c_to_asm_raw_reference_occurrences':state['asm_resolved_refs'],
        'c_to_asm_scope':'archive/vmlinux only; separate object-provider evidence, not AST definitions',
        'remaining_gaps':['nested_macro_dependency','callback_and_descriptor_relations','transitive_internal_implementation',
                          'config_constraints','assembly_sections_attributes','implicit_ABI_and_memory_model']})
    e.save_json(output/f'result_{build.arch}.json',summary)
    return summary

def full_merge(build,output):
    """Only called by small selftests in this audit; kernel work uses staged main."""
    state=initialize(build);advance(build,state,len([en for en in build.entries if en.is_c]))
    return finalize(build,state,output)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arch',choices=e.ARCHES)
    parser.add_argument('--limit',type=int,default=128)
    args=parser.parse_args()
    if args.limit<1:parser.error('--limit must be positive')
    for name in ['criteria','criteria_amendment2']:
        if e.sha256(HERE/f'{name}.md')!=(HERE/f'{name}_sha256.txt').read_text().split()[0]:
            raise ValueError(f'{name} frozen digest changed')
    build=e.kernel_build(args.arch)
    if build.inputs!=e.load_json(OLD/f'result_{args.arch}.json')['inputs']:
        raise ValueError('Inputs differ from original completed enumeration')
    identity=e.digest({'inputs':build.inputs,'policy':e.sha256(HERE/'repair_policy.py'),
                       'driver':e.sha256(Path(__file__)),'amendment2':e.sha256(HERE/'criteria_amendment2.md')})
    output=HERE/'revised'/args.arch/identity
    output.mkdir(parents=True,exist_ok=True)
    checkpoint=output/'checkpoint.pickle'
    if not checkpoint.exists():
        state=initialize(build);frozen_merge.save(checkpoint,state)
        e.save_json(output/'inputs.json',build.inputs)
        print(f'{args.arch}: initialized; rerun same command for reference batches',flush=True)
        return
    with checkpoint.open('rb') as stream:state=pickle.load(stream)
    if state.get('complete'):print(f'{args.arch}: complete: {output}');return
    complete=advance(build,state,args.limit)
    if complete:
        result=finalize(build,state,output);state['complete']=True
        (output/'complete.txt').write_text('success\n',encoding='utf-8')
        print(f'{args.arch}: complete: {result["symbols"]} AST symbols / {result["points"]} AST points',flush=True)
    frozen_merge.save(checkpoint,state)
    print(f'{args.arch}: checkpoint {state["offset"]}; output={output}',flush=True)

if __name__=='__main__':main()
