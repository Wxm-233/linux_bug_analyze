#!/bin/bash
# lpaeinv criteria 三: boot an arm LPAE kernel (keep/<K>/zImage) with the stress /init. WSL root.
#   K=inv bash run.sh <tag>
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/lpaeinv_20261122
W=/root/work/lpaeinv
K=${K:-inv}; T=${1:-run}
timeout 700 qemu-system-arm -M virt,highmem=off -cpu cortex-a15 -smp 2 -m 1G \
  -kernel $W/keep/$K/zImage -initrd $W/keep/init.cpio \
  -append "console=ttyAMA0 panic=-1 rdinit=/init" -nographic -no-reboot > $R/logs/run_${K}_${T}.log 2>&1
echo "exit $? (K=$K T=$T)" | tee -a $R/logs/run_${K}_${T}.log
