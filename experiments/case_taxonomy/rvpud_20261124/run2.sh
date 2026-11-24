# rvpud criteria2 三: bash run2.sh <tag> <img:arch:name:mode>...   logs -> runs/<tag>/<name>.run<i>.log  (RUNS, PAR env)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/rvpud_20261124
tag=$1; shift
W=/root/work/rvpud; mkdir -p $W/ird $R/runs/$tag
for a in riscv:riscv64-linux-gnu x86_64:x86_64-linux-gnu; do
  arch=${a%%:*}; cc=${a##*:}
  st=$W/ird/stage_$arch; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
  ${cc}-gcc -static -O2 -w -o $st/init $R/rvpud.c || exit 1
  (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/$arch.cpio
done
one() {  # one <tag> <img> <arch> <name> <mode> <run>
  local tag=$1 img=$2 arch=$3 name=$4 mode=$5 i=$6
  local log=$R/runs/$tag/${name}.run$i.log
  local dev=(-object memory-backend-memfd,id=shm,size=2G,share=on -device ivshmem-plain,memdev=shm)
  local app="console=ttyS0 panic=-1 loglevel=8 nokaslr vfio.enable_unsafe_noiommu_mode=1 rvpud=$mode"
  local cmd
  case $arch in
    riscv) cmd=(qemu-system-riscv64 -M virt -cpu rv64 -bios default) ;;
    x86_64) cmd=(qemu-system-x86_64 -M q35 -cpu max) ;;
  esac
  timeout --kill-after=10s 400s "${cmd[@]}" -accel tcg -nographic -no-reboot -smp 2 -m 1024M "${dev[@]}" \
    -kernel $img -initrd $W/ird/$arch.cpio -append "$app" < /dev/null > $log 2>&1
  echo "$tag $name run$i exit=$? end=$(grep -ac '@@END 0' $log) badpud=$(grep -ac 'bad pud' $log) oops=$(grep -acE 'Oops|Kernel panic' $log) warn=$(grep -acE 'WARNING:|BUG:' $log)"
}
export -f one; export R W
jobs=$W/jobs_$tag.txt; : > $jobs
for i in $(seq 1 ${RUNS:-3}); do for k in "$@"; do
  IFS=: read img arch name mode <<< "$k"; echo "$tag $img $arch $name $mode $i" >> $jobs
done; done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-3} -L 1 bash -c 'one "$@"' _ < $jobs
echo "$tag done $(date '+%T')"
