# kcov_pa: build, run propsuite3 on both kernel sets, symbolize. WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/kcov_pa_20261115
K=/root/work/kcov_pa/kernels
bash $R/build.sh
bash $R/run.sh head $K riscv_head:riscv:plain x86_64_head:x86_64:plain arm64_head:arm64:plain arm64_head:arm64:mte
bash $R/run.sh x1pre $K riscv_x1pre:riscv:plain x86_64_x1pre:x86_64:plain arm64_x1pre:arm64:plain arm64_x1pre:arm64:mte
cd $R && python3 symbolize_inline.py head > symbolize_head.txt 2>&1; python3 symbolize_inline.py x1pre > symbolize_x1pre.txt 2>&1
echo "run_all end $(date '+%T')"
