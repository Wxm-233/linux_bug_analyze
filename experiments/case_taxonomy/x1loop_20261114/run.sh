# Run the property probe on the X1 kernels (x1loop criteria 三). WSL.
#   bash run.sh        logs -> runs/<kernel>_<mode>.run<i>.log
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/x1loop_20261114
W=/root/work/x1loop; K=$W/kernels; mkdir -p $W/ird $R/runs
for a in riscv:riscv64-linux-gnu arm64:aarch64-linux-gnu x86_64:x86_64-linux-gnu; do
  arch=${a%%:*}; cc=${a##*:}
  st=$W/ird/stage_$arch; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
  ${cc}-gcc -static -O2 -Wall -o $st/init $R/zprobe.c || exit 1
  (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/$arch.cpio
done
one() {  # one <arch> <kernel tag> <mode> <run>
  local arch=$1 kt=$2 mode=$3 i=$4
  local log=$R/runs/${kt}_${mode}.run$i.log   # separate statement: `local a=.. b=$a` expands $a before assigning
  local common=(-accel tcg -nographic -no-reboot -smp 2 -m 1024M -kernel $K/$kt.img -initrd $W/ird/$arch.cpio)
  case $arch in
    riscv) cmd=(qemu-system-riscv64 -M virt -cpu rv64 -bios default "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5') ;;
    arm64) if [ $mode = mte ]; then m=virt,mte=on; else m=virt; fi
           cmd=(qemu-system-aarch64 -M $m -cpu max "${common[@]}" -append 'console=ttyAMA0 panic=-1 loglevel=5') ;;
    x86_64) cmd=(qemu-system-x86_64 -M q35 -cpu max "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5') ;;
  esac
  timeout --kill-after=10s 1800s "${cmd[@]}" < /dev/null > $log 2>&1
  echo "$kt $mode run$i exit=$? end=$(grep -ac '^@@END' $log) rounds=$(grep -ac '\"round\"' $log)"
}
export -f one; export R W K
jobs=$W/jobs.txt; : > $jobs
for v in pre fix; do
  for i in 1 2 3; do
    [ -f $K/riscv_$v.img ] && echo "riscv riscv_$v plain $i" >> $jobs
    [ -f $K/x86_64_$v.img ] && echo "x86_64 x86_64_$v plain $i" >> $jobs
    [ -f $K/arm64_$v.img ] && { echo "arm64 arm64_$v plain $i" >> $jobs; echo "arm64 arm64_$v mte $i" >> $jobs; }
  done
done
echo "jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-8} -L 1 bash -c 'one "$@"' _ < $jobs
echo "done $(date '+%T')"
