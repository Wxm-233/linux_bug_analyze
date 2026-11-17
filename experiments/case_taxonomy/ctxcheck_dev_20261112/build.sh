# Build the 4 debug + PREEMPT_RT kernels of A175 (ctxcheck criteria 四) and extract pipeline facts of the pre-fix
# riscv tree (criteria 三, for reach_any). Runs in WSL.   bash build.sh
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/ctxcheck_dev_20261112
W=/root/work/ctxcheck; S=$W/src; K=$W/kernels; mkdir -p $W $K
FIX=969f028bf2c4; PARENT=$(git -C $KSRC rev-parse --short=12 $FIX^)
OPTS="DEBUG_KERNEL DEBUG_ATOMIC_SLEEP PROVE_LOCKING DEBUG_VM DEBUG_VM_PGTABLE PAGE_TABLE_CHECK PAGE_TABLE_CHECK_ENFORCED DEBUG_LIST DEBUG_SG DEBUG_VIRTUAL SCHED_STACK_END_CHECK DEBUG_IRQFLAGS"
LOG=$R/build.log; : > $LOG; : > $R/config_check.txt
echo "A175 fix $FIX parent $PARENT start $(date '+%F %T')" | tee -a $LOG
rm -rf $S; mkdir -p $S; git -C $KSRC archive --format=tar $PARENT | tar -x -C $S
cfg() {  # cfg <name> <karch> <defconfig>
  local O=$W/b_$1; mkdir -p $O
  make -C $S O=$O ARCH=$2 LLVM=1 $3 > $O.cfg.log 2>&1 || return 1
  local args="-e EXPERT -e PREEMPT_RT -d PREEMPT_NONE -d PREEMPT_VOLUNTARY -d PREEMPT -d PREEMPT_LAZY"
  for o in $OPTS; do args="$args -e $o"; done
  $S/scripts/config --file $O/.config $args
  make -C $S O=$O ARCH=$2 LLVM=1 olddefconfig >> $O.cfg.log 2>&1 || return 1
  for o in PREEMPT_RT $OPTS LOCKDEP PROVE_RCU DEBUG_SPINLOCK DEBUG_MUTEXES; do
    echo "$1 $o $(grep -c "^CONFIG_$o=y" $O/.config)" >> $R/config_check.txt
  done
  grep -q '^CONFIG_PREEMPT_RT=y' $O/.config || { echo "$1 PREEMPT_RT NOT SET" | tee -a $LOG; return 1; }  # amendment 1
}
bld() {  # bld <name> <karch> <defconfig> <image target> <image path in tree>
  local O=$W/b_$1 t0=$(date +%s)
  cfg $1 $2 $3 || { echo "$1 CONFIG FAILED" | tee -a $LOG; return 1; }
  if make -C $S O=$O ARCH=$2 LLVM=1 -j20 $4 > $O.build.log 2>&1; then
    cp $O/$5 $K/$1.img; cp $O/.config $K/$1.config; cp $O/vmlinux $K/$1.vmlinux
    echo "$1 BUILD OK $(( $(date +%s)-t0 ))s" | tee -a $LOG
  else
    echo "$1 BUILD FAILED $(( $(date +%s)-t0 ))s: $(grep -a -m3 ' error' $O.build.log | tr '\n' ' ' | cut -c1-400)" | tee -a $LOG; return 1
  fi
}
bld a175_pre riscv defconfig Image arch/riscv/boot/Image
(cd $S && python3 scripts/clang-tools/gen_compile_commands.py -d $W/b_a175_pre -o $W/cc_pre.json) > $W/cc.log 2>&1 \
  && echo "cc OK $(python3 -c "import json;print(len(json.load(open('$W/cc_pre.json'))))") units" | tee -a $LOG
bld a175_ref_arm64 arm64 defconfig Image arch/arm64/boot/Image
bld a175_ref_x86_64 x86 x86_64_defconfig bzImage arch/x86/boot/bzImage
# facts of the pre-fix riscv tree (frozen extractor copy of heldout_v2, TARGET=riscv)
t0=$(date +%s)
TARGET=riscv PYTHONPATH=$REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline PYTHONDONTWRITEBYTECODE=1 \
  python3 $REPO/experiments/case_taxonomy/heldout_v2_20261111/static/extract3.py $W/cc_pre.json $S $W/facts_pre.json.gz --jobs 16 > $W/extract.log 2>&1 \
  && echo "facts OK $(( $(date +%s)-t0 ))s $(tail -1 $W/extract.log | cut -c1-120)" | tee -a $LOG || echo "facts FAILED" | tee -a $LOG
# fix: apply the fix diff (not printed) and rebuild riscv incrementally
git -C $KSRC diff --binary $PARENT $FIX > $W/fix.diff
if (cd $S && git apply --whitespace=nowarn $W/fix.diff) && t0=$(date +%s) && make -C $S O=$W/b_a175_pre ARCH=riscv LLVM=1 -j20 Image > $W/fix.build.log 2>&1; then
  cp $W/b_a175_pre/arch/riscv/boot/Image $K/a175_fix.img; cp $W/b_a175_pre/.config $K/a175_fix.config; cp $W/b_a175_pre/vmlinux $K/a175_fix.vmlinux
  echo "a175_fix BUILD OK $(( $(date +%s)-t0 ))s rebuilt=$(grep -c ' CC ' $W/fix.build.log)" | tee -a $LOG
else echo "a175_fix BUILD FAILED" | tee -a $LOG; fi
rm -f $W/fix.diff
echo "end $(date '+%F %T') $(du -sh $W | cut -f1); kernels: $(ls $K | tr '\n' ' ')" | tee -a $LOG
