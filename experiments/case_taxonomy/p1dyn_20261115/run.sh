# p1dyn criteria 四: run pdyn as /init.  bash run.sh <tag> <img:arch:name>...   logs -> runs/<tag>/<name>.run<i>.log
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/p1dyn_20261115
tag=$1; shift
W=/root/work/p1dyn; mkdir -p $W/ird $R/runs/$tag
for a in riscv:riscv64-linux-gnu arm64:aarch64-linux-gnu x86_64:x86_64-linux-gnu; do
  arch=${a%%:*}; cc=${a##*:}
  st=$W/ird/stage_$arch; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
  ${cc}-gcc -static -O2 -Wall -pthread -o $st/init $R/pdyn.c || exit 1
  (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/$arch.cpio
done
one() {  # one <tag> <img> <arch> <name> <run>
  local tag=$1 img=$2 arch=$3 name=$4 i=$5
  local log=$R/runs/$tag/${name}.run$i.log
  local numa=(-object memory-backend-ram,id=m0,size=512M -object memory-backend-ram,id=m1,size=512M
              -numa node,nodeid=0,cpus=0,memdev=m0 -numa node,nodeid=1,cpus=1,memdev=m1)
  local common=(-accel tcg -nographic -no-reboot -smp 2 -m 1024M "${numa[@]}" -kernel $img -initrd $W/ird/$arch.cpio)
  local cmd
  case $arch in
    riscv) cmd=(qemu-system-riscv64 -M virt -cpu rv64 -bios default "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5 nokaslr') ;;
    arm64) cmd=(qemu-system-aarch64 -M virt -cpu max "${common[@]}" -append 'console=ttyAMA0 panic=-1 loglevel=5 nokaslr') ;;
    x86_64) cmd=(qemu-system-x86_64 -M q35 -cpu max "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5 nokaslr') ;;
  esac
  timeout --kill-after=10s 1800s "${cmd[@]}" < /dev/null > $log 2>&1
  echo "$tag $name run$i exit=$? end=$(grep -ac '^@@END' $log)"
}
export -f one; export R W
jobs=$W/jobs_$tag.txt; : > $jobs
for i in $(seq 1 ${RUNS:-3}); do for k in "$@"; do
  IFS=: read img arch name <<< "$k"; echo "$tag $img $arch $name $i" >> $jobs
done; done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-8} -L 1 bash -c 'one "$@"' _ < $jobs
echo "$tag done $(date '+%T')"
