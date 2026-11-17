source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux grep -n -e 'pgd_alloc(' -e 'pgd_free(' -e PGD_TABLE_SIZE dde30854bddf^ -- arch/powerpc/mm arch/powerpc/include/asm/pgalloc.h arch/powerpc/include/asm/book3s/64/pgalloc.h arch/x86/mm/pgtable.c
git -C /root/repos/linux show dde30854bddf^:arch/powerpc/include/asm/book3s/64/pgalloc.h | sed -n '1,180p'
git -C /root/repos/linux grep -n -e HUGE_PMD_SHARE -e 'huge_pmd_unshare(' a4a118f2eead^ -- arch mm/hugetlb.c
git -C /root/repos/linux show bd1f2b2ace84^:arch/x86/include/asm/pgtable_64.h | sed -n '180,250p'
git -C /root/repos/linux grep -n -e _PAGE_SWP_SOFT_DIRTY -e _PAGE_SWP_UFFD_WP -e _PAGE_ACCESSED -e _PAGE_DIRTY bd1f2b2ace84^ -- arch/x86/include/asm/pgtable_types.h
