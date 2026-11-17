source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux show 3faa3ebc89c1^:arch/arm64/include/asm/pgtable.h | sed -n '1200,1255p;1410,1450p'
git -C /root/repos/linux grep -n -e 'ptep_test_and_clear_young' -e 'PTE_AF' 3faa3ebc89c1^ -- arch/arm64/include/asm/pgtable.h arch/arm64/include/asm/pgtable-hwdef.h
git -C /root/repos/linux show bd1f2b2ace84^:arch/x86/include/asm/pgtable.h | sed -n '175,225p;255,280p'
git -C /root/repos/linux show 7f9c9b607dc2^:arch/arm/mm/flush.c | sed -n '60,145p'
git -C /root/repos/linux show dde30854bddf^:arch/x86/mm/pgtable.c | sed -n '300,355p'
git -C /root/repos/linux grep -n -e '__pgd_alloc' -e 'PGALLOC_GFP' dde30854bddf^ -- include/asm-generic/pgalloc.h arch/x86/include/asm/pgalloc.h
