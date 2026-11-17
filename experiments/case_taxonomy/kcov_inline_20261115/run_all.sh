# kcov_inline amendment 1: rerun propsuite3 on the debug-info riscv/x86_64 kernels. WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/kcov_inline_20261115
K=/root/work/kcov_inline/kernels
bash $R/run.sh head $K riscv_head:riscv:plain x86_64_head:x86_64:plain
bash $R/run.sh x1pre $K riscv_x1pre:riscv:plain x86_64_x1pre:x86_64:plain
echo "run_all end $(date '+%T')"
