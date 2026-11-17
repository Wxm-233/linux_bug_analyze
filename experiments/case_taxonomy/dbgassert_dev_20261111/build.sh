# Build the three debug-assertion kernels of the current version (dbgassert criteria 二). Runs in WSL.
#   bash build.sh        -> /root/work/dbgassert/build/<arch>/ ; config_check.txt and build.log in this directory
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/dbgassert_dev_20261111
B=/root/work/dbgassert/build
OPTS="DEBUG_KERNEL DEBUG_ATOMIC_SLEEP PROVE_LOCKING DEBUG_VM DEBUG_VM_PGTABLE PAGE_TABLE_CHECK PAGE_TABLE_CHECK_ENFORCED DEBUG_LIST DEBUG_SG DEBUG_VIRTUAL SCHED_STACK_END_CHECK DEBUG_IRQFLAGS"
LOG=$R/build.log; : > $LOG; : > $R/config_check.txt
echo "source $(git -C $KSRC rev-parse --short=12 HEAD) dirty=$(git -C $KSRC status --porcelain | wc -l) start $(date '+%F %T')" | tee -a $LOG
for spec in riscv:riscv:Image arm64:arm64:Image x86_64:x86:bzImage; do
  IFS=: read name karch img <<< "$spec"
  O=$B/$name; mkdir -p $O; t0=$(date +%s)
  mk() { make -C $KSRC O=$O ARCH=$karch LLVM=1 "$@"; }
  if [ $name = x86_64 ]; then mk x86_64_defconfig > $O.cfg.log 2>&1; else mk defconfig > $O.cfg.log 2>&1; fi || { echo "$name DEFCONFIG FAILED" | tee -a $LOG; continue; }
  args=""; for o in $OPTS; do args="$args -e $o"; done
  $KSRC/scripts/config --file $O/.config $args
  mk olddefconfig >> $O.cfg.log 2>&1 || { echo "$name OLDDEFCONFIG FAILED" | tee -a $LOG; continue; }
  for o in $OPTS LOCKDEP PROVE_RCU TRACE_IRQFLAGS DEBUG_SPINLOCK DEBUG_MUTEXES; do
    echo "$name $o $(grep -c "^CONFIG_$o=y" $O/.config)" >> $R/config_check.txt
  done
  if mk -j20 $img > $O.build.log 2>&1; then
    f=$O/arch/$karch/boot/$img
    echo "$name BUILD OK $(( $(date +%s) - t0 ))s image=$(stat -c %s $f) bytes" | tee -a $LOG
  else
    echo "$name BUILD FAILED $(( $(date +%s) - t0 ))s: $(tail -n 8 $O.build.log | tr '\n' ' ' | cut -c1-600)" | tee -a $LOG
  fi
done
echo "end $(date '+%F %T')  $(du -sh $B | cut -f1)" | tee -a $LOG
