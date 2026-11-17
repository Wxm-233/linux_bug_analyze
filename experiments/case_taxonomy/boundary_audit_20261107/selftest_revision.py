"""Minimal real ELF/AST regression plus ambiguity, scope and generated-pool checks."""
from pathlib import Path
import gzip
import json
import os
import pickle
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'boundary_enum_20261106'))
import enumerate as e
import repair_policy as p
import remerge
import report_revised

FILES={
'kernel/weak.c':'__attribute__((weak)) int api(void) { return -1; }\n',
'kernel/strong.c':'int api(void) { return 7; }\n',
'arch/test/caller.c':'extern int api(void);\nint caller(void) { return api(); }\n',
'kernel/use.c':'extern int asm_api(void);\nint user(void) { return asm_api(); }\n',
'arch/test/internal.c':'extern int asm_api(void);\nint internal(void) { return asm_api(); }\n',
'arch/test/provider.S':'.text\n.globl asm_api\n.type asm_api,@function\nasm_api:\n mov $1, %eax\n ret\n.size asm_api,.-asm_api\n',
}

def main():
    work=Path(os.environ['KBUILD'])/'enumeration/boundary_audit_20261107_revision_selftest'
    source=HERE/'selftest_revision_src';source.mkdir(exist_ok=True)
    work.mkdir(parents=True,exist_ok=True)
    rows=[];objects=[]
    for name,text in FILES.items():
        file=source/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text,encoding='utf-8')
        obj=str(Path(name).with_suffix('.o'));(work/obj).parent.mkdir(parents=True,exist_ok=True)
        argv=['clang','--target=x86_64-linux-gnu','-fno-pie','-c','-o',obj,str(file)]
        e.command(argv,cwd=work);objects.append(obj)
        rows.append({'directory':str(work),'file':str(file),'arguments':argv})
    e.save_json(work/'compile_commands.json',rows)
    e.command(['llvm-ar','crsT','vmlinux.a',*objects],cwd=work)
    e.command(['ld.lld','-e','user','-o','vmlinux','--whole-archive','vmlinux.a'],cwd=work)
    build=e.Build('regression',source,work,e.load_entries(work/'compile_commands.json'),
                  work/e.digest({'fixtures':FILES,'parser':e.sha256(HERE.parent/'boundary_enum_20261106/enumerate.py')}),{})
    e.scan(build,jobs=1,limit=20)
    state=remerge.initialize(build)
    remerge.advance(build,state,2)
    # Exercise a real checkpoint round trip, not just two in-memory slices.
    checkpoint=work/'regression_checkpoint.pickle'
    remerge.frozen_merge.save(checkpoint,state)
    with checkpoint.open('rb') as stream:state=pickle.load(stream)
    remerge.advance(build,state,20)
    result=remerge.finalize(build,state,work)
    syms=e.load_json(work/'symbols_regression.json')
    with gzip.open(work/'boundary_regression.jsonl.gz','rt') as stream:points=[json.loads(l) for l in stream]
    api=[x for x in syms if x['name']=='api']
    assert len(api)==1 and api[0]['definition']['file']=='kernel/strong.c',api
    assert len(points)==1 and points[0]['direction']=='arch_to_public',points
    assert state['bindings']['api']['has_weak_competitor']
    with gzip.open(work/'c_to_asm_regression.jsonl.gz','rt') as stream:asm=[json.loads(l) for l in stream]
    assert len(asm)==2,asm
    assert {r['use']['file']:r['direction'] for r in asm}=={'kernel/use.c':'public_to_arch','arch/test/internal.c':None},asm
    assert all(r['definition']['source']=='arch/test/provider.S' and r['definition']['line'] is None for r in asm)
    # The old resolver reproduces the public/public weak ambiguity on the same fixture.
    caller=e.load_json(build.unit_path(build.entries[2]))
    s=next(e.Symbol.from_row(s) for s in caller['symbols'] if s[1]=='api')
    assert e.resolve(s,True,state['definitions'],state['by_object'],{})==(None,'ambiguous_definition')
    assert p.resolve_c(s,False,state['definitions'],state['by_object'],{},state['bindings'],e.resolve)==(None,'ambiguous_definition')
    assert p.choose([('a.o','T'),('b.o','T')],{'T'}) is None
    assert p.choose([('a.o','W'),('b.o','W')],{'W'}) is None
    assert p.choose([('a.o','T')],{'W'}) is None
    assert p.choose([('a.o','W')],{'W'})==('a.o','W')
    assert p.asm_provider(s,False,state['bindings']) is None
    assert not p.runtime_point('@build/arch/test/foo.mod.c',['@build/arch/test/foo.mod.c'])
    assert not p.runtime_point('include/public.h',['@build/scripts/kconfig/parser.tab.c'])
    assert p.runtime_point('@build/arch/test/include/generated/asm/syscall_table.h',['arch/test/syscall_table.c'])
    assert p.runtime_point('@build/lib/generated_table.c',['@build/lib/generated_table.c'])
    # Per-unit exclusion must preserve a shared header point used by a runtime TU.
    assert not p.runtime_point('include/public.h',['scripts/host.c'])
    assert p.runtime_point('include/public.h',['kernel/runtime.c'])
    report={'status':'passed','AST_points':len(points),'C_to_asm_points':len(asm),'C_to_asm_cross_points':1,
            'checks':['public_strong_public_weak','old_ambiguity_reproduced','module_scope_not_overridden','checkpoint_round_trip',
                      'C_to_asm_cross_and_internal','nonunique_providers_rejected','final_binding_checked',
                      'module_metadata_pool','host_pool','generated_syscall_kept','generated_runtime_kept',
                      'shared_header_unit_filter'],'revised_result':result}
    fixture_summary=report_revised.summarize_one(work,'regression',result)
    assert fixture_summary['revised_AST']['points']==1 and fixture_summary['C_to_asm_cross_points']==1
    assert fixture_summary['strong_weak_competitions_with_selected_winner']==1
    report['checks'].append('revision_report_fixture')
    e.save_json(HERE/'selftest_revision_result.json',report)
    print('REVISION SELFTEST PASSED',len(points),'AST points,',len(asm),'C-to-asm points')

if __name__=='__main__':main()
