source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux show b7795074a046^:arch/parisc/mm/hugetlbpage.c | sed -n '95,155p'
git -C /root/repos/linux grep -n -e 'kvm_vm_ioctl_create_vcpu' -e 'kvm_arch_vcpu_postcreate(vcpu)' -e 'create_vcpu_fd(vcpu)' 496e0f706b8a^ -- virt/kvm/kvm_main.c
git -C /root/repos/linux grep -n -e 'tlb_flush(tlb)' -e 'hash__tlb_flush(' 1665c027afb2^ -- mm/mmu_gather.c include/asm-generic/tlb.h arch/powerpc/include/asm/book3s/64 arch/powerpc/mm
git -C /root/repos/linux grep -n -e 'free_initmem();' -e 'mark_readonly();' -e 'mark_rodata_ro();' -e 'jump_label_init_ro();' 213aa670153e^ -- init/main.c kernel/jump_label.c
git -C /root/repos/linux grep -n -e 'earlycon_map(' -e 'FIX_EARLYCON_MEM' -e 'ioremap(' 1037d186edfc^ -- drivers/tty/serial/earlycon.c
git -C /root/repos/linux show b49f700668ff^:arch/riscv/mm/tlbflush.c | sed -n '1,180p'
git -C /root/repos/linux show b49f700668ff^:arch/riscv/include/asm/tlbflush.h | sed -n '1,155p'
