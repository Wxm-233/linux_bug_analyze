from collect import *

def main():
    d=read(HERE/'evidence/unresolved_compilation.json')
    entries=e.load_entries(BASE/'riscv_defconfig/compile_commands.json')
    paths=e.Paths(KSRC,BASE/'riscv_defconfig')
    f='fs/quota/kqid.c'
    d[f]={'entries':[en.number for en in entries if paths.name(str(en.source))==f], 'symbols':[],
          'config_controls':run(['grep','-n','-E','^#if|^#else|^#endif',f])}
    archive=set(e.command(['llvm-ar','t','vmlinux.a'],cwd=BASE/'riscv_defconfig').splitlines())
    for f,r in d.items():
        r['archive_objects']=[str(entries[i].output.relative_to(BASE/'riscv_defconfig')) for i in r['entries'] if str(entries[i].output.relative_to(BASE/'riscv_defconfig')) in archive]
    write('evidence/unresolved_compilation.json',d)
    write('evidence/unresolved_details.json',[
        run(['grep','-n','-E','CONFIG_NUMA|CONFIG_LOCKDEP|CONFIG_QUOTA|CONFIG_PCI_P2PDMA|CONFIG_DEBUG_PAGEALLOC|CONFIG_LEDS_CLASS|CONFIG_IRQ_DOMAIN|CONFIG_UDP_TUNNEL|CONFIG_CRYPTO_LIB_SHA512|CONFIG_SHADOW_CALL_STACK|CONFIG_QUEUED_SPINLOCKS', '.config'],BASE/'riscv_defconfig'),
        run(['sed','-n','100,130p','kernel/locking/qspinlock.c']),
        run(['sed','-n','1260,1310p','include/linux/seqlock.h']),
        run(['sed','-n','375,395p','include/linux/lockdep.h']),
        run(['grep','-n','-E','sha512|udp_tunnel','modules.order'],BASE/'riscv_defconfig'),
        run(['grep','-n','-E','SYM_FUNC|ENTRY|END','arch/riscv/lib/memcpy.S','arch/riscv/lib/memset.S','arch/riscv/lib/strlen.S','arch/riscv/lib/strcmp.S','arch/riscv/lib/uaccess.S','arch/riscv/mm/page.S'])])
    print('archive membership added')
if __name__=='__main__':main()
