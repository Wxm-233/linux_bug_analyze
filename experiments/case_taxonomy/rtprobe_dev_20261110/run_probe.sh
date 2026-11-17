# Boot every kernel listed in kernels_all.txt twice with the probe program as /init (rtprobe criteria 三).
#   bash run_probe.sh        logs -> runs/probe/<kernel>.run<i>.log.gz in this directory
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
CT=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
R=$CT/rtprobe_dev_20261110; W=/root/work/rtprobe
mkdir -p $W/runs $W/initramfs $R/runs/probe
for arch in riscv arm64 x86_64; do
  case $arch in
    riscv) cc=riscv64-linux-gnu-gcc ;;
    arm64) cc=aarch64-linux-gnu-gcc ;;
    x86_64) cc=x86_64-linux-gnu-gcc ;;
  esac
  stage=$W/stage_$arch; rm -rf $stage; mkdir -p $stage/dev $stage/proc $stage/sys
  $cc -static -O2 -Wall -Wl,-Ttext-segment=0x400000 -o $stage/init $R/harness/rt_probe.c || exit 1
  (cd $stage && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/initramfs/probe_$arch.cpio
done
jobs=$W/jobs.txt; : > $jobs
while read name arch img; do
  [ -z "$name" ] && continue
  for i in 1 2; do echo "$arch $img $W/initramfs/probe_$arch.cpio $W/runs/$name.run$i.log" >> $jobs; done
done < <(tr -d '\r' < $R/kernels_all.txt)
echo "jobs: $(wc -l < $jobs)  start $(date +%T)"
xargs -P ${PAR:-10} -L 1 bash $CT/casemodel_dev_20261110/harness/run_qemu.sh < $jobs
echo "done $(date +%T)"
for f in $W/runs/*.log; do grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > $R/runs/probe/$(basename $f).gz; done
