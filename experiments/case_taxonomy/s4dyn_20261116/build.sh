# s4dyn criteria 二: mglru-profile kernels via kbuild
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/s4dyn_20261116
mkdir -p $R/kernels
echo "start $(date '+%T')"
for a in arm64 x86_64 riscv; do
  ( img=$($KB get df2908090cda $a mglru 2>$R/kernels/build_${a}_plain.err); echo "$a plain rc=$? $img" ) &
done
wait
echo "plain done $(date '+%T')"
for m in p1dyn.json:F2 s4dyn.json:F4; do
  img=$($KB get df2908090cda arm64 mglru --mut $m 2>$R/kernels/build_arm64_${m##*:}.err); echo "arm64 $m rc=$? $img"
done
echo "end $(date '+%T')"
for a in arm64 x86_64 riscv; do
  c=/root/work/kbuild/trees/df2908090cda_${a}_mglru/out/.config
  echo "== $a"; grep -E '^CONFIG_(LRU_GEN|LRU_GEN_ENABLED|NUMA|MIGRATION|TRANSPARENT_HUGEPAGE|ZONE_DEVICE|DEVICE_PRIVATE|TEST_HMM|MEMCG|SWAP|ZRAM)=' $c | tr '\n' ' '; echo
done
