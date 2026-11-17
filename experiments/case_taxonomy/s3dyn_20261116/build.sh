# s3dyn criteria 二: dax-profile x86_64 kernels via kbuild (plain, then F3 incremental)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/s3dyn_20261116
mkdir -p $R/kernels
echo "start $(date '+%T')"
img=$($KB get df2908090cda x86_64 dax 2>$R/kernels/build_plain.err); echo "plain rc=$? $img"
img=$($KB get df2908090cda x86_64 dax --mut s3dyn.json:F3 2>$R/kernels/build_F3.err); echo "F3 rc=$? $img"
echo "end $(date '+%T')"
$KB list | grep '|dax|'
c=/root/work/kbuild/trees/df2908090cda_x86_64_dax/out/.config
grep -E '^CONFIG_(USERFAULTFD|PTE_MARKER_UFFD_WP|MEMORY_HOTPLUG|MEMORY_HOTREMOVE|ZONE_DEVICE|FS_DAX|DAX|LIBNVDIMM|BLK_DEV_PMEM|X86_PMEM_LEGACY|EXT4_FS|DEVTMPFS|TRANSPARENT_HUGEPAGE)=' $c
grep -h 'WARNING config' $R/kernels/build_*.err
df -h / | tail -1
