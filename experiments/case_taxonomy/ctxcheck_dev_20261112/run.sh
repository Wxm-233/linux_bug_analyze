# Run the trap cases and the syscall cases on the 4 A175 kernels, 3 times each (ctxcheck criteria 五). WSL.
#   bash run.sh        logs -> runs/{trap,sys}/<kernel>.run<i>.log.gz
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
CT=$REPO/experiments/case_taxonomy; R=$CT/ctxcheck_dev_20261112; W=/root/work/ctxcheck; K=$W/kernels
mkdir -p $W/ird $W/runs/trap $W/runs/sys $R/runs/trap $R/runs/sys
for a in riscv:riscv64-linux-gnu arm64:aarch64-linux-gnu x86_64:x86_64-linux-gnu; do
  arch=${a%%:*}; cc=${a##*:}
  st=$W/ird/stage_trap_$arch; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
  ${cc}-gcc -static -O2 -Wall -o $st/init $R/harness/trap_runner.c || exit 1
  cp $R/cases/trap.txt $st/cases.txt
  (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/trap_$arch.cpio
  bash $CT/heldout_prep_20261110/harness/mk_initramfs.sh $arch $R/cases/sys_$arch.txt $W/ird/sys_$arch.cpio > /dev/null || exit 1
done
jobs=$W/jobs.txt; : > $jobs
for k in a175_pre:riscv a175_fix:riscv a175_ref_arm64:arm64 a175_ref_x86_64:x86_64; do
  name=${k%%:*}; arch=${k##*:}
  for t in trap sys; do for i in 1 2 3; do
    echo "$arch $K/$name.img $W/ird/${t}_$arch.cpio $W/runs/$t/$name.run$i.log" >> $jobs
  done; done
done
echo "jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-12} -L 1 bash $CT/dbgassert_dev_20261111/harness/run_qemu_dbg.sh < $jobs
echo "done $(date '+%T')"
for t in trap sys; do for f in $W/runs/$t/*.log; do
  grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > $R/runs/$t/$(basename $f).gz
done; done
