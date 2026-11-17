from collect import *

def main():
    queries=[]
    for name in ['__sbi_ecall','__sbi_base_ecall','sbi_err_map_linux_errno','elf_find_pbase',
                 'bpf_arch_uaddress_limit','bpf_do_misc_fixups','acpi_idle_lpi_enter',
                 'vmemmap_start_pfn','VMEMMAP_ADDR_ALIGN']:
        queries.append(run(['git','grep','-n','-w','-e',name,'--','arch/riscv','include','kernel','lib','mm','drivers/acpi']))
    architecture_entries={}
    for arch in ['riscv','arm64','x86_64']:
        entries=e.load_entries(BASE/f'{arch}_defconfig/compile_commands.json')
        architecture_entries[arch]=[{'id':en.number,'source':str(en.source),'object':str(en.output)} for en in entries if str(en.source).endswith(('arch/arm64/kernel/syscall.c','arch/riscv/kernel/sbi_ecall.c'))]
    write('evidence/sample_final_queries.json',{'queries':queries,'architecture_compile_entries':architecture_entries})
    for q in queries[:4]:print(q['stdout'],end='')
if __name__=='__main__':main()
