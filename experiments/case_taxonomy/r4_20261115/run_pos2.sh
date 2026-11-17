# r4 amendment 1: rebuild mutants with __HAVE_ARCH_MOVE_PTE, rerun the positive group. WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/r4_20261115
bash $R/build.sh
bash $R/run.sh pos /root/work/r4/kernels riscv_R4a:riscv:plain riscv_R4b:riscv:plain x86_64_R4a:x86_64:plain x86_64_R4b:x86_64:plain
echo "run_pos2 end $(date '+%T')"
