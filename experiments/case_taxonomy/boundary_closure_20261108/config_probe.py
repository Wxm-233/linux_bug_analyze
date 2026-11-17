"""Collect exact local Kconfig stanzas; never change or build the source tree."""
import re
from common import *

NAMES='NONPORTABLE ARCH_RV32I ARCH_RV64I 64BIT MMU BPF BPF_SYSCALL BPF_JIT BPF_JIT_ALWAYS_ON HAVE_EBPF_JIT KEXEC KEXEC_FILE CRASH_DUMP CRYPTO CRYPTO_SHA256 ARCH_SUPPORTS_KEXEC ARCH_SUPPORTS_KEXEC_FILE KPROBES KRETPROBES KRETPROBE_ON_REHOOK RETHOOK HAVE_RETHOOK FUNCTION_TRACER FUNCTION_GRAPH_TRACER DYNAMIC_FTRACE TRANSPARENT_HUGEPAGE DEBUG_PAGEALLOC KASAN KASAN_GENERIC KFENCE MEMORY_HOTPLUG MEMORY_HOTREMOVE SPARSEMEM_VMEMMAP RISCV_USER_CFI RISCV_ISA_ZICFISS RISCV_ISA_ZICFILP SHADOW_CALL_STACK CFI CFI_CLANG PTDUMP_DEBUGFS BINFMT_FLAT IOMMU_DMA RISCV_IOMMU PCI RV RV_MON_SLEEP RV_MON_RTAPP MLX5_CORE MLX5_CORE_EN NETDEVICES ETHERNET NET_VENDOR_MELLANOX INET SMP PGTABLE_LEVELS GENERIC_GETTIMEOFDAY HAVE_ARCH_BINFMT_FLAT ARCH_HAS_BINFMT_FLAT'.split()
NAMES += 'ARCH_SUPPORTS_SHADOW_CALL_STACK ARCH_SUPPORTS_CFI KRETPROBE_ON_RETHOOK RV_PER_TASK_MONITORS'.split()
NAMES += 'HAVE_SHADOW_CALL_STACK ARCH_HAS_PTDUMP ARCH_ENABLE_MEMORY_HOTPLUG ARCH_SUPPORTS_DEBUG_PAGEALLOC'.split()
if (HERE/'config_matrix.json').is_file():
    for profile in read(HERE/'config_matrix.json')['profiles']:
        NAMES += list(profile['requests'])+list(profile['expect'])
NAMES=sorted(set(NAMES))

def main():
    pattern=r'^[[:space:]]*(menu)?config ('+'|'.join(NAMES)+r')$'
    result=git('grep','-n','-E',pattern,'--','*Kconfig*')
    records={n:[] for n in NAMES}
    for line in result.splitlines():
        file,num,text=line.split(':',2)
        name=text.split()[-1]
        data=(KSRC/file).read_text(encoding='utf-8',errors='replace').splitlines()
        i=int(num)-1
        j=i+1
        while j<len(data) and not re.match(r'^\s*(?:menu)?config |^\s*endchoice|^\s*endmenu|^\s*endif',data[j]): j+=1
        records[name].append({'file':file,'line':i+1,'stanza':'\n'.join(data[i:j]),
                              'preceding_context':'\n'.join(data[max(0,i-10):i]),'source_sha256':sha(KSRC/file)})
    write('evidence/kconfig_stanzas.json',records)
    print('collected',len(records),'symbols, missing',[n for n,r in records.items() if not r])
    queries={}
    for name in ('SHADOW_CALL_STACK','CFI_CLANG','KRETPROBE_ON_REHOOK','HAVE_RETHOOK','RISCV_USER_CFI','ARCH_HAS_BINFMT_FLAT'):
        queries[name]=git('grep','-n','-w',name,'--','arch/riscv/Kconfig','arch/arm64/Kconfig','arch/Kconfig','fs/Kconfig.binfmt',optional=True)
    write('evidence/kconfig_support_queries.json',queries)
    for n,v in queries.items(): print(n,v)
    capability={}
    for name,args in {
        'riscv_user_cfi':['clang','--target=riscv64-linux-gnu','-mabi=lp64','-march=rv64ima_zicfiss_zicfilp','-fcf-protection=full','-fsyntax-only','-x','c','/dev/null'],
        'riscv_kcfi':['clang','--target=riscv64-linux-gnu','-fsanitize=kcfi','-fsyntax-only','-x','c','/dev/null'],
    }.items():
        p=subprocess.run(args,capture_output=True,text=True)
        capability[name]={'command':args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    write('evidence/compiler_capabilities.json',capability)
    print('compiler capabilities',capability)

if __name__=='__main__': main()
