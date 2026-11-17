# z5fix criteria 三: positive, regression and negative groups. WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/z5fix_20261115
bash $R/run.sh pos2 /root/work/mutation2/kernels riscv_N2:riscv:plain x86_64_N2:x86_64:plain arm64_N2:arm64:plain riscv_N3:riscv:plain x86_64_N3:x86_64:plain
bash $R/run.sh pos3 /root/work/mutation3/kernels riscv_N2r:riscv:plain arm64_N3a:arm64:plain
bash $R/run.sh head /root/work/proprules/kernels riscv_head:riscv:plain x86_64_head:x86_64:plain arm64_head:arm64:plain
