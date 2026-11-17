# p1dyn criteria 三: dyn-profile kernels via kbuild (plain x3 arch in parallel, then F1/F2 on x86_64/arm64)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/p1dyn_20261115
mkdir -p $R/kernels
echo "start $(date '+%T')"
for a in riscv x86_64 arm64; do
  ( img=$($KB get df2908090cda $a dyn 2>$R/kernels/build_${a}_plain.err); echo "$a plain rc=$? $img" ) &
done
wait
for a in x86_64 arm64; do
  ( for m in F1 F2; do img=$($KB get df2908090cda $a dyn --mut p1dyn.json:$m 2>$R/kernels/build_${a}_$m.err); echo "$a $m rc=$? $img"; done ) &
done
wait
echo "end $(date '+%T')"
$KB list | grep '|dyn|'
for a in riscv x86_64 arm64; do
  c=/root/work/kbuild/trees/df2908090cda_${a}_dyn/out/.config
  echo "== $a"; grep -E '^CONFIG_(NUMA|MIGRATION|TRANSPARENT_HUGEPAGE|ARCH_ENABLE_THP_MIGRATION|ZONE_DEVICE|DEVICE_PRIVATE|TEST_HMM|MEMCG|SWAP|ZRAM|LRU_GEN|X86_USER_SHADOW_STACK|MEMORY_FAILURE|MEMORY_HOTREMOVE)=' $c | tr '\n' ' '; echo
done
