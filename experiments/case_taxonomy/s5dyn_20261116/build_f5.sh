source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/s5dyn_20261116
for a in arm64 x86_64 riscv; do
  ( img=$($KB get df2908090cda $a dbgvm --mut s5dyn.json:F5 2>$R/kernels/build_${a}_F5_retry.err); echo "$a F5 rc=$? $img" ) &
done
wait
