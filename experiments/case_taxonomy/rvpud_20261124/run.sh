# rvpud criteria 四: bash run.sh <tag> <img:name:mode>...   logs -> runs/<tag>/<name>.run<i>.log  (RUNS, PAR env)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/rvpud_20261124
tag=$1; shift
W=/root/work/rvpud; mkdir -p $W/ird $R/runs/$tag
st=$W/ird/stage; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
riscv64-linux-gnu-gcc -static -O2 -Wall -o $st/init $R/rvpud.c || exit 1
(cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/riscv.cpio
one() {  # one <tag> <img> <name> <mode> <run>
  local tag=$1 img=$2 name=$3 mode=$4 i=$5
  local log=$R/runs/$tag/${name}.run$i.log
  timeout --kill-after=10s 300s qemu-system-riscv64 -M virt -cpu rv64 -bios default -accel tcg -nographic -no-reboot \
    -smp 2 -m 1024M -object memory-backend-memfd,id=shm,size=2G,share=on -device ivshmem-plain,memdev=shm \
    -kernel $img -initrd $W/ird/riscv.cpio \
    -append "console=ttyS0 panic=-1 loglevel=8 nokaslr vfio.enable_unsafe_noiommu_mode=1 rvpud=$mode" < /dev/null > $log 2>&1
  echo "$tag $name run$i exit=$? end=$(grep -ac '^@@END' $log) badpud=$(grep -ac 'bad pud' $log)"
}
export -f one; export R W
jobs=$W/jobs_$tag.txt; : > $jobs
for i in $(seq 1 ${RUNS:-3}); do for k in "$@"; do
  IFS=: read img name mode <<< "$k"; echo "$tag $img $name $mode $i" >> $jobs
done; done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-3} -L 1 bash -c 'one "$@"' _ < $jobs
echo "$tag done $(date '+%T')"
