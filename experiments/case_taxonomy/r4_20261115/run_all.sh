# r4 criteria 四: build mutants, then negative / positive / coverage runs, then symbolize. WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/r4_20261115
bash $R/build.sh
bash $R/run.sh neg /root/work/proprules/kernels riscv_head:riscv:plain x86_64_head:x86_64:plain arm64_head:arm64:plain
bash $R/run.sh pos /root/work/r4/kernels riscv_R4a:riscv:plain riscv_R4b:riscv:plain x86_64_R4a:x86_64:plain x86_64_R4b:x86_64:plain
bash $R/run.sh kcov /root/work/kcov_pa/kernels riscv_head:riscv:plain x86_64_head:x86_64:plain arm64_head:arm64:plain
cd $R && python3 symbolize_inline.py kcov > symbolize_kcov.txt 2>&1
echo "run_all end $(date '+%T')"
