#!/bin/bash
# lpaeqemu: boot probes to find why /init prints nothing (diagnosis, not a test group)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/lpaeqemu_20261122
W=/root/work/lpaeqemu
name=$1; shift
timeout 120 qemu-system-arm -M virt,highmem=on -cpu cortex-a15 -smp 1 "$@" -kernel $W/keep/${K:-base}/zImage -initrd $W/keep/init.cpio \
  -nographic -no-reboot > $R/logs/probe_${K:-base}_$name.log 2>&1
echo "probe $name exit $?"
