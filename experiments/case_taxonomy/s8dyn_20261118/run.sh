# s8dyn criteria 三: bash run.sh <tag>   runs the 5 cells x RUNS (default 3); logs -> runs/<tag>/<cell>.run<i>.log
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/s8dyn_20261118
tag=$1
W=/root/work/s8dyn; mkdir -p $W $R/runs/$tag
for a in riscv x86; do
  st=$W/stage_$a; rm -rf $st; mkdir -p $st/dev $st/proc $st/sys $st/tmp
  cc=riscv64-linux-gnu-gcc; [ $a = x86 ] && cc=x86_64-linux-gnu-gcc
  $cc -static -O2 -Wall -o $st/init $R/s8.c || exit 1
  (cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/$a.cpio
done
RV=$(cat $R/kernels/riscv_${KDPA:-dpa}.path); RVF=$(cat $R/kernels/riscv_${KDPA:-dpa}_F8.path); X86=$(cat $R/kernels/x86_dpa.path)
one() {  # one <tag> <cell> <run>
  local tag=$1 cell=$2 i=$3 log=$R/runs/$1/$2.run$3.log
  local rv=(timeout --kill-after=10s ${TMO:-300}s qemu-system-riscv64 -cpu rv64 -bios default -accel ${ACCEL:-tcg} -nographic -no-reboot -smp 4 -m 2048M -initrd $W/riscv.cpio)
  local x86=(timeout --kill-after=10s ${TMO:-300}s qemu-system-x86_64 -accel tcg -nographic -no-reboot -smp 4 -m 2048M -initrd $W/x86.cpio)
  local base="panic=-1 loglevel=5 nokaslr"
  case $cell in
    A) "${rv[@]}" -M virt,aia=aplic-imsic -kernel $RV  -append "console=ttyS0 $base debug_pagealloc=on" ;;
    B) "${rv[@]}" -M virt,aia=aplic-imsic -kernel $RVF -append "console=ttyS0 $base debug_pagealloc=on" ;;
    C) "${rv[@]}" -M virt,aia=aplic-imsic -kernel $RV  -append "console=ttyS0 $base debug_pagealloc=off" ;;
    D) "${rv[@]}" -M virt                 -kernel $RV  -append "console=ttyS0 $base debug_pagealloc=on" ;;
    E) "${x86[@]}"                        -kernel $X86 -append "console=ttyS0 $base debug_pagealloc=on" ;;
  esac < /dev/null > $log 2>&1
  echo "$tag $cell run$i exit=$? end=$(grep -ac '^@@END' $log)"
}
export -f one; export R W RV RVF X86
jobs=$W/jobs_$tag.txt; : > $jobs
for i in $(seq 1 ${RUNS:-3}); do for c in ${CELLS:-A B C D E}; do echo "$tag $c $i" >> $jobs; done; done
echo "$tag jobs $(wc -l < $jobs) start $(date '+%T')"
xargs -P ${PAR:-5} -L 1 bash -c 'one "$@"' _ < $jobs
echo "$tag done $(date '+%T')"
