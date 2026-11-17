# Run the 36 cases (12 kinds x 3) on a set of kernels, 3 times each, QEMU -smp 2 (ctxcheck2 amendment 1). WSL.
#   bash run.sh <tag> <kernel dir> <name:arch>...     logs -> runs/<tag>/<name>.run<i>.log.gz
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/ctxcheck2_dev_20261112
tag=$1; KD=$2; shift 2
W=/root/work/ctxcheck2/run_$tag; rm -rf $W; mkdir -p $W/ird $W/logs $R/runs/$tag
for a in riscv:riscv64-linux-gnu arm64:aarch64-linux-gnu x86_64:x86_64-linux-gnu; do
  arch=${a%%:*}; cc=${a##*:}
  st=$W/ird/stage_$arch; mkdir -p $st/dev $st/proc $st/sys $st/tmp
  ${cc}-gcc -static -O2 -w -o $st/init $R/harness/runner2.c || exit 1
  cp $R/cases/cases.txt $st/cases.txt
  (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/$arch.cpio
done
jobs=$W/jobs.txt; : > $jobs
for k in "$@"; do name=${k%%:*}; arch=${k##*:}
  for i in 1 2 3; do echo "$arch $KD/$name.img $W/ird/$arch.cpio $W/logs/$name.run$i.log" >> $jobs; done
done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-12} -L 1 bash $R/harness/run_qemu_dbg2.sh < $jobs
echo "$tag done $(date '+%T')"
for f in $W/logs/*.log; do grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > $R/runs/$tag/$(basename $f).gz; done
