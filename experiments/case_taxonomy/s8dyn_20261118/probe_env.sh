# s8dyn: environment probe only (not counted): is IMSIC stable with single-thread TCG or -smp 2?  logs -> runs/probe/
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/s8dyn_20261118; W=/root/work/s8dyn; mkdir -p $R/runs/probe
RV=$(cat $R/kernels/riscv_dpa.path)
p() { timeout --kill-after=10s 400s qemu-system-riscv64 -cpu rv64 -bios default -nographic -no-reboot -m 2048M -initrd $W/riscv.cpio \
      -M virt,aia=aplic-imsic -kernel $RV -append "console=ttyS0 panic=-1 loglevel=5 nokaslr debug_pagealloc=off" "$@"; }
p -accel tcg,thread=single -smp 4 < /dev/null > $R/runs/probe/C_single_smp4.log 2>&1 &
p -accel tcg -smp 2 < /dev/null > $R/runs/probe/C_mttcg_smp2.log 2>&1 &
wait
for f in $R/runs/probe/*.log; do echo "$(basename $f): stalls=$(grep -ac 'rcu_sched detected stalls' $f) workers=$(grep -ac '^@@WORKER' $f) power=$(grep -ac 'Power down' $f) end=$(grep -ac '@@END' $f)"; done
