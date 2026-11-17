# Kernels of the two feasible samples (ctxcheck2 amendment 1, 四) + static check of the riscv sample (六). WSL.
#   bash build.sh <tag> <fix commit> <target arch name> [extra config symbols...]
#   arch names: riscv arm64 x86_64.  Kernels -> /root/work/ctxcheck2/kernels/<tag>_{pre,fix,ref_<arch>}.{img,config,vmlinux}
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/ctxcheck2_dev_20261112; CV=$REPO/experiments/case_taxonomy/checks_v1_20261108
tag=$1; FIX=$2; TGT=$3; shift 3; EXTRA="$*"
W=/root/work/ctxcheck2/$tag; S=$W/src; K=/root/work/ctxcheck2/kernels; mkdir -p $W $K
PARENT=$(git -C $KSRC rev-parse --short=12 $FIX^)
OPTS="DEBUG_KERNEL DEBUG_ATOMIC_SLEEP PROVE_LOCKING DEBUG_VM DEBUG_VM_PGTABLE PAGE_TABLE_CHECK PAGE_TABLE_CHECK_ENFORCED DEBUG_LIST DEBUG_SG DEBUG_VIRTUAL SCHED_STACK_END_CHECK DEBUG_IRQFLAGS"
LOG=$R/build_$tag.log; : > $LOG; CC=$R/config_check_$tag.txt; : > $CC
echo "$tag fix $FIX parent $PARENT target $TGT extra [$EXTRA] start $(date '+%F %T')" | tee -a $LOG
rm -rf $S; mkdir -p $S; git -C $KSRC archive --format=tar $PARENT | tar -x -C $S
karch() { case $1 in riscv) echo riscv;; arm64) echo arm64;; x86_64) echo x86;; esac; }
defc() { case $1 in x86_64) echo x86_64_defconfig;; *) echo defconfig;; esac; }
img() { case $1 in riscv) echo arch/riscv/boot/Image;; arm64) echo arch/arm64/boot/Image;; x86_64) echo arch/x86/boot/bzImage;; esac; }
bld() {  # bld <kernel name> <arch name>
  local n=$1 a=$2 O=$W/b_$2 t0=$(date +%s) ka=$(karch $2)
  mkdir -p $O
  make -C $S O=$O ARCH=$ka LLVM=1 $(defc $a) > $O.cfg.log 2>&1 || { echo "$n DEFCONFIG FAILED" | tee -a $LOG; return 1; }
  local args=""; for o in $OPTS $EXTRA; do args="$args -e $o"; done
  $S/scripts/config --file $O/.config $args
  make -C $S O=$O ARCH=$ka LLVM=1 olddefconfig >> $O.cfg.log 2>&1
  for o in $OPTS $EXTRA UPROBES PERF_EVENTS LOCKDEP UNMAP_KERNEL_AT_EL0; do echo "$n $o $(grep -c "^CONFIG_$o=y" $O/.config)" >> $CC; done
  for o in $EXTRA; do grep -q "^CONFIG_$o=y" $O/.config || { echo "$n EXTRA $o NOT SET" | tee -a $LOG; return 1; }; done
  if make -C $S O=$O ARCH=$ka LLVM=1 -j20 $(basename $(img $a)) > $O.build.log 2>&1; then
    cp $O/$(img $a) $K/$n.img; cp $O/.config $K/$n.config; cp $O/vmlinux $K/$n.vmlinux
    echo "$n BUILD OK $(( $(date +%s)-t0 ))s" | tee -a $LOG
  else
    echo "$n BUILD FAILED $(( $(date +%s)-t0 ))s: $(grep -a -m3 -E ' error|Error ' $O.build.log | tr '\n' ' ' | cut -c1-400)" | tee -a $LOG; return 1
  fi
}
ctx() {  # ctx <pre|fix>: execution-context checker of checks_v1 on the riscv tree (amendment 1, 六)
  local O=$W/b_riscv cache=$W/ctxcache_$1
  (cd $S && python3 scripts/clang-tools/gen_compile_commands.py -d $O -o $O/compile_commands.json) > $W/cc_$1.log 2>&1
  python3 -B $CV/ctx_extract.py $O $cache --jobs 12 --source $S > $W/ctx_extract_$1.log 2>&1 \
    && python3 -B $CV/ctx_analyze.py $cache $S/arch/riscv/kernel/entry.S $R/ctxflags_${tag}_$1.json > $W/ctx_analyze_$1.log 2>&1 \
    && echo "ctx $1 OK $(tail -1 $W/ctx_extract_$1.log | cut -c1-150)" | tee -a $LOG || echo "ctx $1 FAILED $(tail -2 $W/ctx_extract_$1.log $W/ctx_analyze_$1.log | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG
  rm -rf $cache
}
bld ${tag}_pre $TGT || { echo "$tag: target pre-fix build failed, stop" | tee -a $LOG; exit 1; }
[ $TGT = riscv ] && ctx pre
for a in riscv arm64 x86_64; do [ $a = $TGT ] || bld ${tag}_ref_$a $a; done
git -C $KSRC diff --binary $PARENT $FIX > $W/fix.diff
if (cd $S && git apply --whitespace=nowarn $W/fix.diff) && t0=$(date +%s) && make -C $S O=$W/b_$TGT ARCH=$(karch $TGT) LLVM=1 -j20 $(basename $(img $TGT)) > $W/fix.build.log 2>&1; then
  cp $W/b_$TGT/$(img $TGT) $K/${tag}_fix.img; cp $W/b_$TGT/.config $K/${tag}_fix.config; cp $W/b_$TGT/vmlinux $K/${tag}_fix.vmlinux
  echo "${tag}_fix BUILD OK $(( $(date +%s)-t0 ))s rebuilt=$(grep -c ' CC ' $W/fix.build.log)" | tee -a $LOG
  [ $TGT = riscv ] && ctx fix
else echo "${tag}_fix BUILD FAILED" | tee -a $LOG; fi
rm -f $W/fix.diff; rm -rf $S $W/b_riscv $W/b_arm64 $W/b_x86_64
echo "end $(date '+%F %T') $(du -sh $W | cut -f1)" | tee -a $LOG
