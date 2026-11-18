# s8dyn criteria 二: build riscv dpa, riscv dpa+F8, x86_64 dpa via kbuild (reuses registered images)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"
R=$REPO/experiments/case_taxonomy/s8dyn_20261118
mkdir -p $R/kernels
( $KB get df2908090cda riscv dpa > $R/kernels/riscv_dpa.path 2> $R/build_riscv.log; echo "riscv dpa exit=$?" >> $R/build.log
  $KB get df2908090cda riscv dpa --mut s8dyn.json:F8 > $R/kernels/riscv_dpa_F8.path 2> $R/build_riscv_f8.log; echo "riscv F8 exit=$?" >> $R/build.log ) &
( $KB get df2908090cda x86_64 dpa > $R/kernels/x86_dpa.path 2> $R/build_x86.log; echo "x86 dpa exit=$?" >> $R/build.log ) &
wait
echo "all builds done $(date '+%T')" >> $R/build.log
