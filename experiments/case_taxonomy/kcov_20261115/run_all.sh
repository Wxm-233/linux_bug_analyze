# kcov criteria 二～四: wait for build.sh, run propsuite3 on both kernel sets, symbolize. WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/kcov_20261115
until grep -q "^end " $R/build.log 2>/dev/null; do sleep 20; done
K=/root/work/kcov/kernels
bash $R/run.sh head $K riscv_head:riscv:plain x86_64_head:x86_64:plain arm64_head:arm64:plain arm64_head:arm64:mte
bash $R/run.sh x1pre $K riscv_x1pre:riscv:plain x86_64_x1pre:x86_64:plain arm64_x1pre:arm64:plain arm64_x1pre:arm64:mte
cd $R && python3 symbolize.py head $K > symbolize_head.txt && python3 symbolize.py x1pre $K > symbolize_x1pre.txt
echo "run_all end $(date '+%T')"
