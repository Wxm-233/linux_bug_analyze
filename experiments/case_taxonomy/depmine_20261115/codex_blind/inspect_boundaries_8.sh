source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=cat
git -C /root/repos/linux show 7f9c9b607dc2^:arch/mips/mm/c-r4k.c | sed -n '575,615p;640,735p'
git -C /root/repos/linux show 835e5ac3f98e^:include/asm-generic/hugetlb.h | sed -n '105,145p'
git -C /root/repos/linux show 835e5ac3f98e^:mm/hugetlb.c | sed -n '5150,5210p'
git -C /root/repos/linux show dde30854bddf^:include/asm-generic/pgalloc.h | sed -n '255,285p'
