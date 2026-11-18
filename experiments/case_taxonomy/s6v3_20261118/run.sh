# s6v3 (copy of s6dyn run.sh): run s6 as /init on arm64.  bash run.sh <tag> <img:name:mode>...   logs -> runs/<tag>/<name>.run<i>.log
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/s6v3_20261118; SRC=$REPO/experiments/case_taxonomy/s6dyn_20261116
tag=$1; shift
W=/root/work/s6v3; mkdir -p $W/ird $R/runs/$tag
st=$W/ird/stage; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
aarch64-linux-gnu-gcc -static -O2 -Wall -o $st/init $SRC/s6.c || exit 1
(cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/arm64.cpio
one() {  # one <tag> <img> <name> <mode> <run>
  local tag=$1 img=$2 name=$3 mode=$4 i=$5
  local log=$R/runs/$tag/${name}.run$i.log
  timeout --kill-after=10s 300s qemu-system-aarch64 -M virt -cpu cortex-a72 -accel tcg -nographic -no-reboot -smp 2 -m 4096M \
    -kernel $img -initrd $W/ird/arm64.cpio -append "console=ttyAMA0 panic=-1 loglevel=5 nokaslr s6mode=$mode" < /dev/null > $log 2>&1
  echo "$tag $name run$i exit=$? end=$(grep -ac '^@@END' $log)"
}
export -f one; export R W
jobs=$W/jobs_$tag.txt; : > $jobs
for i in $(seq 1 ${RUNS:-3}); do for k in "$@"; do
  IFS=: read img name mode <<< "$k"; echo "$tag $img $name $mode $i" >> $jobs
done; done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-6} -L 1 bash -c 'one "$@"' _ < $jobs
echo "$tag done $(date '+%T')"
