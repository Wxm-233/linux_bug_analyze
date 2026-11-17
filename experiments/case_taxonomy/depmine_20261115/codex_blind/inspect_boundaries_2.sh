source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux show 721a73e30c9e^:include/linux/mm.h | sed -n '4900,4955p'
git -C /root/repos/linux show 099dd6878b9b^:arch/x86/include/asm/pgtable.h | sed -n '750,775p;1310,1368p'
git -C /root/repos/linux grep -n HAVE_ARCH_USERFAULTFD_WP 099dd6878b9b^ -- arch fs/userfaultfd.c
git -C /root/repos/linux show ad1ac596e8a8^:include/linux/pgtable.h | sed -n '85,110p'
git -C /root/repos/linux grep -n -e 'config HIGHPTE' -e 'select HIGHPTE' ad1ac596e8a8^ -- arch
git -C /root/repos/linux show ad1ac596e8a8^:mm/migrate.c | sed -n '250,312p'
git -C /root/repos/linux grep -n migration_entry_wait_on_locked ad1ac596e8a8^ -- mm
