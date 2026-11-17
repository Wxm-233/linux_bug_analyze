source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux show 19b482c29b6f^:arch/arm/include/asm/cacheflush.h | sed -n '245,315p'
git -C /root/repos/linux show 19b482c29b6f^:arch/x86/include/asm/cacheflush.h | sed -n '1,80p'
git -C /root/repos/linux show 19b482c29b6f^:arch/arm/mm/flush.c | sed -n '270,340p'
git -C /root/repos/linux grep -n -e HAVE_ARCH_TRANSPARENT_HUGEPAGE -e 'flush_cache_range' 7f9c9b607dc2^ -- arch/arm/Kconfig arch/arm/mm/flush.c arch/arm/include/asm/cacheflush.h
git -C /root/repos/linux grep -n -e 'static inline int pte_write' -e 'static inline int pte_dirty' -e 'pte_pfn(' -e '__swp_entry(' bd1f2b2ace84^ -- arch/powerpc/include/asm/book3s/64/pgtable.h arch/arm64/include/asm/pgtable.h arch/x86/include/asm/pgtable.h
git -C /root/repos/linux show bd1f2b2ace84^:arch/arm64/include/asm/pgtable.h | sed -n '90,140p'
git -C /root/repos/linux show bd1f2b2ace84^:mm/Kconfig | sed -n '1120,1155p'
