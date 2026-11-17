# s3dyn criteria 三: run s3 as /init.  bash run.sh <tag> <img:name>...   logs -> runs/<tag>/<name>.run<i>.log
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/s3dyn_20261116
tag=$1; shift
W=/root/work/s3dyn; mkdir -p $W $R/runs/$tag
st=$W/stage; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/mnt $st/tmp
x86_64-linux-gnu-gcc -static -O2 -Wall -o $st/init $R/s3.c || exit 1
rm -f $st/fs.img; truncate -s 32M $st/fs.img
mkfs.ext4 -F -q -b 4096 $st/fs.img || exit 1
(cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/s3.cpio
rm -rf $st
one() {  # one <tag> <img> <name> <run>
  local tag=$1 img=$2 name=$3 i=$4
  local log=$R/runs/$tag/${name}.run$i.log
  timeout --kill-after=10s 900s qemu-system-x86_64 -M q35 -cpu max -accel tcg -nographic -no-reboot -smp 2 -m 1024M \
    -kernel $img -initrd $W/s3.cpio -append 'console=ttyS0 panic=-1 loglevel=5 nokaslr memmap=256M!512M' < /dev/null > $log 2>&1
  echo "$tag $name run$i exit=$? end=$(grep -ac '^@@END' $log)"
}
export -f one; export R W
jobs=$W/jobs_$tag.txt; : > $jobs
for i in $(seq 1 ${RUNS:-3}); do for k in "$@"; do
  IFS=: read img name <<< "$k"; echo "$tag $img $name $i" >> $jobs
done; done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-6} -L 1 bash -c 'one "$@"' _ < $jobs
echo "$tag done $(date '+%T')"
