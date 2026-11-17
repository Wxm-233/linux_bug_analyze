# Boot each listed kernel twice with the runtime probe as /init (rtprobe_dev_20261110 method). Runs in WSL.
#   bash probe.sh <kernels.txt: "name arch image" per line> <out dir>     -> <out dir>/<name>.run<i>.log.gz
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
CT=$REPO/experiments/case_taxonomy
list=$(realpath -e -- "$1"); out=$2; W=/root/work/heldout_run/probe.$$
mkdir -p $W/runs $W/initramfs "$out"
declare -A CC=([riscv]=riscv64-linux-gnu-gcc [loongarch]=loongarch64-linux-gnu-gcc-14 [arm64]=aarch64-linux-gnu-gcc [x86_64]=x86_64-linux-gnu-gcc)
: > $W/jobs.txt
while read name arch img; do
  [ -z "$name" ] && continue
  if [ ! -f $W/initramfs/$arch.cpio ]; then
    st=$W/stage_$arch; mkdir -p $st/dev $st/proc $st/sys
    ${CC[$arch]} -static -O2 -Wl,-Ttext-segment=0x400000 -o $st/init $CT/rtprobe_dev_20261110/harness/rt_probe.c 2>/dev/null || exit 1
    (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/initramfs/$arch.cpio
  fi
  for i in 1 2; do echo "$arch $img $W/initramfs/$arch.cpio $W/runs/$name.run$i.log" >> $W/jobs.txt; done
done < <(tr -d '\r' < $list)
xargs -P 10 -L 1 bash $CT/difftest_tools_20261111/harness/run_qemu.sh < $W/jobs.txt
for f in $W/runs/*.log; do grep -aq '^@@SH END' $f || echo "INCOMPLETE $f"; gzip -c $f > "$out/$(basename $f).gz"; done
rm -rf $W
