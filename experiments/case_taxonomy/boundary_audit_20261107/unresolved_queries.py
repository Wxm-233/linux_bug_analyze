from collect import *

def main():
    refs=read(HERE/'evidence/unresolved_population.json')
    names=sorted({r['symbol'][1] for r in refs if r['category']=='object_or_function_without_C_definition' and not r['symbol'][1].startswith('__compiletime_assert_')})
    queries=[]
    # One bounded identifier query per name, local tracked source only.
    for name in names:
        q=run(['git','grep','-n','-w','-e',name,'--','include','kernel','lib','mm','fs','net','drivers','arch/riscv','arch/x86'])
        q['name']=name
        # Keep full local output, not just the first hit or a guessed definition.
        queries.append(q)
    for args in [
        ['git','grep','-n','-e','compiletime_assert','--','include/linux/compiler_types.h'],
        ['grep','-n','-E','SYM_FUNC|SYM_CODE|ENTRY|END|_start|clear_page','arch/riscv/lib/memcpy.S','arch/riscv/lib/memset.S','arch/riscv/lib/strlen.S','arch/riscv/lib/uaccess.S','arch/riscv/mm/page.S','arch/riscv/kernel/head.S','arch/riscv/kernel/entry.S'],
        ['git','grep','-n','-E','_stext|__init_begin|__bss_start|__start_rodata|jiffies =','--','include/asm-generic/vmlinux.lds.h','arch/riscv/kernel/vmlinux.lds.S']]:
        queries.append(run(args))
    write('evidence/unresolved_queries.json',queries)
    entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
    paths=e.Paths(KSRC,BASE/'riscv_defconfig')
    inputs=read(OLD/'result_riscv.json')['inputs'];cache=BASE/'enumeration/riscv'/e.digest(inputs)
    source_names=defaultdict(set)
    for q in queries:
        if 'name' not in q:continue
        for line in q['stdout'].splitlines():
            f=line.split(':',1)[0]
            if f.endswith('.c'):source_names[f].add(q['name'])
    # Restrict cache inspection to files that might actually define the uncommon names.
    targets=['lib/bitmap.c','lib/crypto/sha512.c','fs/quota/dquot.c','kernel/irq/irqdesc.c',
             'drivers/pci/p2pdma.c','mm/debug_page_alloc.c','kernel/irq/generic-chip.c',
             'drivers/leds/led-class.c','kernel/locking/qspinlock.c','net/ipv4/udp_tunnel_core.c',
             'net/ipv6/ip6_udp_tunnel.c','arch/riscv/kernel/irq.c']
    compilation={}
    for f in targets:
        ens=[en for en in entries if paths.name(str(en.source))==f]
        compilation[f]={'entries':[en.number for en in ens], 'symbols':[]}
        for en in ens:
            r=read(cache/f'{en.number:05d}.json.gz')
            for n,s in enumerate(r['symbols']):
                if s[1] in source_names.get(f,set()):
                    compilation[f]['symbols'].append({'unit':en.number,'symbol':s,'in_definitions':n in r['definitions']})
        compilation[f]['config_controls']=run(['grep','-n','-E','^#if|^#else|^#endif',f])
    write('evidence/unresolved_compilation.json',compilation)
    print('queries',len(queries))

if __name__=='__main__':main()
