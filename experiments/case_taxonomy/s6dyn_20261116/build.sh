source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/s6dyn_20261116
mkdir -p $R/kernels
echo "start $(date '+%T')"
img=$($KB get df2908090cda arm64 pg64k 2>$R/kernels/build_plain.err); echo "arm64 pg64k plain rc=$? $img"
img=$($KB get df2908090cda arm64 pg64k --mut s6dyn.json:F6 2>$R/kernels/build_F6.err); echo "arm64 pg64k F6 rc=$? $img"
echo "end $(date '+%T')"
grep -E '^CONFIG_(ARM64_64K_PAGES|ARM64_4K_PAGES|TRANSPARENT_HUGEPAGE|SWAP|ZRAM|ZSMALLOC|SHMEM|THP_SWAP|ARCH_FORCE_MAX_ORDER)=' /root/work/kbuild/trees/df2908090cda_arm64_pg64k/out/.config | tr '\n' ' '; echo
