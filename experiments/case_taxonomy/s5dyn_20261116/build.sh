# s5dyn criteria 二: dbgvm-profile kernels via kbuild
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/s5dyn_20261116
mkdir -p $R/kernels
echo "start $(date '+%T')"
for a in arm64 x86_64 riscv; do
  ( img=$($KB get df2908090cda $a dbgvm 2>$R/kernels/build_${a}_plain.err); echo "$a plain rc=$? $img"
    img=$($KB get df2908090cda $a dbgvm --mut s5dyn.json:F5 2>$R/kernels/build_${a}_F5.err); echo "$a F5 rc=$? $img" ) &
done
wait
echo "end $(date '+%T')"
for a in arm64 x86_64 riscv; do
  c=/root/work/kbuild/trees/df2908090cda_${a}_dbgvm/out/.config
  echo "== $a"; grep -E '^CONFIG_(DEBUG_VM|DEBUG_KERNEL|LRU_GEN|TRANSPARENT_HUGEPAGE|DEVICE_PRIVATE|TEST_HMM|MEMCG|ZRAM|SPARSEMEM_VMEMMAP)=' $c | tr '\n' ' '; echo
done
