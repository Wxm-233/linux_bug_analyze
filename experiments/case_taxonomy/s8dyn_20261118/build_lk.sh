# s8dyn amendment 3: riscv dpalk, riscv dpalk+F8
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
KB="python3 $REPO/tools/kbuild/kbuild.py"; R=$REPO/experiments/case_taxonomy/s8dyn_20261118
$KB get df2908090cda riscv dpalk > $R/kernels/riscv_dpalk.path 2> $R/build_lk.log; echo "riscv dpalk exit=$?" >> $R/build.log
$KB get df2908090cda riscv dpalk --mut s8dyn.json:F8 > $R/kernels/riscv_dpalk_F8.path 2> $R/build_lk_f8.log; echo "riscv dpalk F8 exit=$?" >> $R/build.log
grep -h "PROVE_LOCKING\|CONFIG_LOCKDEP=\|DEBUG_PAGEALLOC=" /root/work/kbuild/trees/df2908090cda_riscv_dpalk/out/.config >> $R/build.log
tail -n 3 $R/build.log; cat $R/kernels/riscv_dpalk*.path
