source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/s8dyn_20261118
python3 $REPO/tools/kbuild/kbuild.py get df2908090cda riscv dpa --mut s8dyn.json:F8 > $R/kernels/riscv_dpa_F8.path 2> $R/build_riscv_f8.log; echo "riscv F8 retry exit=$?" >> $R/build.log; cat $R/kernels/riscv_dpa_F8.path
