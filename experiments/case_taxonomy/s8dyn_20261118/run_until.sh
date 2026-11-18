# s8dyn amendment 4: run cells B and C (lockdep kernels) one attempt at a time until 3 valid runs each (max 6). logs -> runs/lk2/
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/s8dyn_20261118; W=/root/work/s8dyn; mkdir -p $R/runs/lk2
RV=$(cat $R/kernels/riscv_dpalk.path); RVF=$(cat $R/kernels/riscv_dpalk_F8.path)
valid() {  # valid <log>
  local f=$1
  grep -aq '@@END' $f && return 0
  grep -aq 'reboot: Power down' $f && [ $(grep -ac '^@@WORKER' $f) -ge 3 ] && return 0
  python3 - "$f" <<'PY' && return 0
import sys
L = open(sys.argv[1], errors="replace").read().split("\n")
sys.exit(0 if any("WARNING:" in l and "kernel/smp.c" in l and any("__kernel_map_pages" in x for x in L[i:i + 40]) for i, l in enumerate(L)) else 1)
PY
  return 1
}
cell() {  # cell <B|C>
  local c=$1 img dpa n=0
  [ $c = B ] && { img=$RVF; dpa=on; } || { img=$RV; dpa=off; }
  for i in 1 2 3 4 5 6; do
    local log=$R/runs/lk2/$c.run$i.log
    timeout --kill-after=10s 1500s qemu-system-riscv64 -M virt,aia=aplic-imsic -cpu rv64 -bios default -accel tcg,thread=single \
      -nographic -no-reboot -smp 4 -m 2048M -initrd $W/riscv.cpio -kernel $img \
      -append "console=ttyS0 panic=-1 loglevel=5 nokaslr debug_pagealloc=$dpa" < /dev/null > $log 2>&1
    local rc=$?
    if valid $log; then n=$((n+1)); v=valid; else v=invalid; fi
    echo "lk2 $c run$i exit=$rc $v (valid so far $n) $(date '+%T')"
    [ $n -ge 3 ] && break
  done
}
echo "lk2 start $(date '+%T')"
cell B > $R/run_lk2_B.log 2>&1 &
cell C > $R/run_lk2_C.log 2>&1 &
wait
cat $R/run_lk2_B.log $R/run_lk2_C.log
echo "lk2 done $(date '+%T')"
