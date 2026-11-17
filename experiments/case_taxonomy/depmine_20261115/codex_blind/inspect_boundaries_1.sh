source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux grep -n -e vmemmap_can_optimize -e ARCH_WANT_OPTIMIZE_DAX_VMEMMAP 721a73e30c9e^ -- mm include arch
git -C /root/repos/linux show 721a73e30c9e^:mm/sparse-vmemmap.c | sed -n '70,140p;180,230p;510,560p'
git -C /root/repos/linux grep -n -e HAVE_ARCH_USERFAULTFD_WP -e 'pte_swp_uffd_wp(' -e 'pte_same(' 099dd6878b9b^ -- arch/x86/include/asm/pgtable.h arch/x86/Kconfig arch/Kconfig include/linux/pgtable.h fs/userfaultfd.c
git -C /root/repos/linux grep -n -e 'pte_unmap(' -e CONFIG_HIGHPTE ad1ac596e8a8^ -- include/linux/pgtable.h arch/x86/include/asm/pgtable_32.h arch/arm/include/asm/highmem.h arch/x86/Kconfig arch/arm/Kconfig mm/migrate.c mm/swap.c
git -C /root/repos/linux grep -n -e ARCH_HAS_PTE_DEVMAP -e ARCH_HAS_DEVICE_EXCLUSIVE -e DEVICE_PRIVATE bd1f2b2ace84^ -- mm/Kconfig arch/x86/Kconfig arch/powerpc/Kconfig arch/arm64/Kconfig
