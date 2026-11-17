source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux show 496e0f706b8a^:virt/kvm/kvm_main.c | sed -n '4220,4255p'
git -C /root/repos/linux show 1665c027afb2^:arch/powerpc/mm/book3s64/hash_tlb.c | sed -n '150,180p'
git -C /root/repos/linux show 213aa670153e^:init/main.c | sed -n '1420,1449p;1462,1485p'
git -C /root/repos/linux show 1037d186edfc^:drivers/tty/serial/earlycon.c | sed -n '35,55p'
git -C /root/repos/linux grep -n -e HAVE_ARCH_TRANSPARENT_HUGEPAGE -e 'r4k_flush_cache_page' -e 'r4k_flush_cache_range' 7f9c9b607dc2^ -- arch/mips/Kconfig arch/mips/mm/c-r4k.c
git -C /root/repos/linux grep -n -e huge_ptep_set_wrprotect -e pmdp_set_access_flags 835e5ac3f98e^ -- include/asm-generic/hugetlb.h mm/hugetlb.c mm/huge_memory.c
git -C /root/repos/linux show b49f700668ff^:arch/riscv/include/asm/errata_list.h | sed -n '1,175p'
