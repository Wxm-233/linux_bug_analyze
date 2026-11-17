"""Targeted cache/nm replay of B446 and one C-to-asm miss, not a kernel merge."""
from collect import *
import repair_policy as policy

def main():
    entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
    selected=read(HERE/'evidence/aio_debug.json')
    archive=set(e.command(['llvm-ar','t','vmlinux.a'],BASE/'riscv_defconfig').splitlines())
    definitions=defaultdict(dict);by_object=defaultdict(set)
    for r in selected:
        obj=str(entries[r['id']].output.relative_to(BASE/'riscv_defconfig'))
        assert obj in archive
        for row in r['symbols'].values():
            if row['in_definitions']:
                s=e.Symbol.from_row(row['row']);definitions[(s.kind,s.usr)][s]=True
                by_object[(obj,s.kind,s.link_name)].add(s)
    target_names={'__riscv_compat_sys_io_pgetevents_time64','__riscv_sys_io_pgetevents','memcpy'}
    files=['fs/aio.o','kernel/sys_ni.o','arch/riscv/lib/memcpy.o']
    providers=defaultdict(set);final=defaultdict(set);nm_evidence=[]
    for obj,name,code in e.read_nm(files+['vmlinux'],BASE/'riscv_defconfig'):
        if name not in target_names:continue
        nm_evidence.append({'object':obj,'name':name,'type':code})
        if obj=='vmlinux':final[name].add(code)
        elif code in e.STRONG_NM|e.WEAK_NM:providers[name].add((obj,code))
    sources={str(en.output.relative_to(BASE/'riscv_defconfig')):e.Paths(KSRC,BASE/'riscv_defconfig').name(str(en.source)) for en in entries}
    bindings=policy.binding_table(providers,final,sources)
    results=[]
    for r in selected[:2]:
        for at,action,num,owner in r['refs']:
            s=e.Symbol.from_row(r['symbols'][str(num)]['row'])
            old,old_reason=e.resolve(s,True,definitions,by_object,{})
            revised,reason=policy.resolve_c(s,True,definitions,by_object,{},bindings,e.resolve)
            assert old is None and old_reason=='ambiguous_definition'
            assert revised is not None and reason is None and revised.at[0]=='fs/aio.c'
            results.append({'use':e.location_json(at),'name':s.name,'old_reason':old_reason,
                            'revised_definition':e.symbol_json(revised),'direction':e.direction(at[0],revised.at[0])})
    ref=next(r for r in read(HERE/'evidence/unresolved_population.json') if r['symbol'][1]=='memcpy' and r['use'][0]=='include/linux/bitmap.h')
    provider=policy.asm_provider(e.Symbol.from_row(ref['symbol']),True,bindings)
    assert provider and provider['source']=='arch/riscv/lib/memcpy.S'
    assert e.direction(ref['use'][0],provider['source'])=='public_to_arch'
    write('real_repairs_verification.json',{'status':'passed','B446_related_references':results,
        'C_to_asm_example':ref|{'revised_provider':provider},'nm_evidence':nm_evidence,
        'nm_command':['llvm-nm','--format=posix','--print-file-name','--extern-only',*files,'vmlinux'],
        'output_filter_names':sorted(target_names),'full_kernel_merge_executed':False})
    print('REAL REPAIRS PASSED',len(results),'pgetevents references; one C-to-asm example')
if __name__=='__main__':main()
