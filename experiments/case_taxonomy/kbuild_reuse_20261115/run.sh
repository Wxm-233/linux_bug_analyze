# Run the rule checks (proprules criteria 四). WSL.
#   bash run.sh <tag> <kernel dir> <kernel:arch:mode>...    logs -> runs/<tag>/<kernel>_<mode>.run<i>.log
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/kbuild_reuse_20261115
tag=$1; KD=$2; shift 2
W=/root/work/kbuild_accept; mkdir -p $W/ird $R/runs/$tag
for a in riscv:riscv64-linux-gnu arm64:aarch64-linux-gnu x86_64:x86_64-linux-gnu; do
  arch=${a%%:*}; cc=${a##*:}
  st=$W/ird/stage_$arch; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
  ${cc}-gcc -static -O2 -Wall -pthread -o $st/init $REPO/experiments/case_taxonomy/r4_20261115/propsuite4.c || exit 1
  (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/$arch.cpio
done
one() {  # one <tag> <kernel dir> <kernel> <arch> <mode> <run>
  local tag=$1 KD=$2 kt=$3 arch=$4 mode=$5 i=$6
  local log=$R/runs/$tag/${kt}_${mode}.run$i.log
  local common=(-accel tcg -nographic -no-reboot -smp 2 -m 1024M -kernel $KD/$kt.img -initrd $W/ird/$arch.cpio)
  local m=virt cmd
  case $arch in
    riscv) cmd=(qemu-system-riscv64 -M virt -cpu rv64 -bios default "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5 nokaslr') ;;
    arm64) [ $mode = mte ] && m=virt,mte=on
           cmd=(qemu-system-aarch64 -M $m -cpu max "${common[@]}" -append 'console=ttyAMA0 panic=-1 loglevel=5 nokaslr') ;;
    x86_64) cmd=(qemu-system-x86_64 -M q35 -cpu max "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5 nokaslr') ;;
  esac
  timeout --kill-after=10s 1800s "${cmd[@]}" < /dev/null > $log 2>&1
  echo "$tag $kt $mode run$i exit=$? end=$(grep -ac '^@@END' $log) lines=$(grep -ac '\"t\":' $log)"
}
export -f one; export R W
jobs=$W/jobs_$tag.txt; : > $jobs
for i in 1 2 3; do for k in "$@"; do
  IFS=: read kt arch mode <<< "$k"; echo "$tag $KD $kt $arch $mode $i" >> $jobs
done; done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-8} -L 1 bash -c 'one "$@"' _ < $jobs
echo "$tag done $(date '+%T')"
