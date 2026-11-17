# Run on the three debug kernels (dbgassert criteria 三). Runs in WSL.
#   bash run_dbg.sh boot            probe program as /init, 2 runs each   -> runs/boot/
#   bash run_dbg.sh cases [g3d]     CUR case set (or its G3d subset), 3 runs each -> runs/cases/
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
CT=$REPO/experiments/case_taxonomy
R=$CT/dbgassert_dev_20261111; B=/root/work/dbgassert/build; W=/root/work/dbgassert/run_$1
mode=$1; sub=${2:-all}
rm -rf $W; mkdir -p $W/runs $W/initramfs $R/runs/$mode
# after the round the build trees were removed; images and .config are kept under /root/work/dbgassert/kernels
K=/root/work/dbgassert/kernels
declare -A IMG=([riscv]=$K/riscv/Image [arm64]=$K/arm64/Image [x86_64]=$K/x86_64/bzImage)
declare -A CC=([riscv]=riscv64-linux-gnu-gcc [arm64]=aarch64-linux-gnu-gcc [x86_64]=x86_64-linux-gnu-gcc)
: > $W/jobs.txt
for a in riscv arm64 x86_64; do
  if [ $mode = boot ]; then
    st=$W/stage_$a; mkdir -p $st/dev $st/proc $st/sys
    ${CC[$a]} -static -O2 -Wl,-Ttext-segment=0x400000 -o $st/init $CT/rtprobe_dev_20261110/harness/rt_probe.c 2>/dev/null || exit 1
    (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/initramfs/$a.cpio
    n=2
  else
    txt=$CT/diverse_dev_20261110/gen/cases_CUR_$a.txt
    if [ $sub = g3d ]; then
      python3 - $CT/diverse_dev_20261110/gen/lists_CUR.json $txt > $W/cases_$a.txt <<'PY'
import json, sys
ids = {str(i) for s in json.load(open(sys.argv[1]))["G3d"].values() for i in s}
sys.stdout.write("".join(l for l in open(sys.argv[2], newline="") if l.split(" ", 1)[0] in ids))
PY
      txt=$W/cases_$a.txt
    fi
    bash $CT/mix_dev_20261110/harness/mk_initramfs.sh $a $txt $W/initramfs/$a.cpio >/dev/null || exit 1
    n=3
  fi
  for i in $(seq 1 $n); do echo "$a ${IMG[$a]} $W/initramfs/$a.cpio $W/runs/dbg_$a.run$i.log" >> $W/jobs.txt; done
done
echo "jobs: $(wc -l < $W/jobs.txt)  start $(date +%s) $(date +%T)"
while read a img cpio log; do
  ( t0=$(date +%s); bash $R/harness/run_qemu_dbg.sh $a $img $cpio $log > $log.rc 2>&1; echo "$(basename $log) $(( $(date +%s) - t0 ))s $(cat $log.rc | tr '\n' ' ')" >> $W/times.txt ) &
done < $W/jobs.txt
wait
echo "done $(date +%s) $(date +%T)"
sort $W/times.txt | tee $R/runs/$mode/times.txt
for f in $W/runs/*.log; do grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > $R/runs/$mode/$(basename $f).gz; done
