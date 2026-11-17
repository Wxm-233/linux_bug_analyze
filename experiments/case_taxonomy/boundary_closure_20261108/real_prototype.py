"""Two targeted existing compile commands, not a full kernel scan."""
import sys
from common import *
from prototype import Unit,macros
sys.path.insert(0,str(OLD))
import enumerate as enumeration

def main():
    check_criteria()
    d=revised()['riscv']
    syms=read(d/'symbols_runtime_riscv.json')
    ids={s['id'] for s in syms if s['name']=='arch_xchg' and s['kind']=='macro'}
    point=next(r for r in lines(d/'boundary_runtime_riscv.jsonl.gz') if r['symbol_id'] in ids)
    build=Path('/root/work/boundary_build/riscv_defconfig')
    entries=enumeration.load_entries(build/'compile_commands.json')
    sparse=next(e for e in entries if e.source==KSRC/'mm/sparse.c')
    cases=[('A058',sparse,{'pfn_to_page','__pfn_to_page','page_to_pfn','__page_to_pfn'},'vmemmap'),
           ('A081',entries[point['units'][0]],{'arch_xchg','arch_xchg_relaxed','xchg','raw_xchg'},'__arch_xchg_masked')]
    results=[]
    (HERE/'evidence/prototype').mkdir(parents=True,exist_ok=True)
    for ident,entry,names,wanted in cases:
        print('targeted parse',ident,entry.number,entry.source,flush=True)
        u=Unit(entry.source,enumeration.parse_args(entry),entry.directory,KSRC,build)
        trace=u.preprocess(HERE/f'evidence/prototype/{ident}.i.gz')
        m=macros(u,trace,root_names=names)
        matches=[r for r in m['expansions'] if wanted in r['dependency_names']]
        assert matches,(ident,'no lexical dependency path to',wanted)
        raw=[r for r in m['recorded_instantiations'] if r['name']==wanted]
        # A lexical definition path is the claim here, even when bindings remain open.
        write(f'evidence/prototype/{ident}_macro_dependencies.json',m)
        row={'id':ident,'unit':entry.number,'source':str(entry.source),'target':wanted,
             'selected_outer_expansions':len(m['expansions']),'outer_with_dependency':len(matches),
             'libclang_direct_target_instantiations':len(raw),
             'pending_outer_regions':sum(r['pending_region'] is not None for r in matches),
             'examples':matches[:2], 'source_sha256':sha(entry.source),
             'compile_commands_sha256':sha(build/'compile_commands.json'),
             'claim':'Targeted potential macro implementation dependency; not added to full runtime pool or sample hit totals.'}
        results.append(row)
        print(ident,'dependency recovered',len(matches),'raw target instances',len(raw),flush=True)
    write('real_prototype_result.json',{'targeted_TUs':len(cases),'cases':results,'full_rescan':False})

if __name__=='__main__':main()
