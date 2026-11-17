# Kernels for the X1 closed loop (x1loop criteria 三). WSL.
#   bash build.sh      -> /root/work/x1loop/kernels/{riscv,x86_64,arm64}_{pre,fix}.{img,config}
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/x1loop_20261114
FIX=5bebe8de1926; PARENT=$(git -C $KSRC rev-parse --short=12 $FIX^)
W=/root/work/x1loop; S=$W/src; K=$W/kernels; mkdir -p $W $K
LOG=$R/build.log; : > $LOG
echo "fix $FIX parent $PARENT start $(date '+%F %T')" | tee -a $LOG
rm -rf $S; mkdir -p $S; git -C $KSRC archive --format=tar $PARENT | tar -x -C $S
karch() { case $1 in riscv) echo riscv;; arm64) echo arm64;; x86_64) echo x86;; esac; }
defc() { case $1 in x86_64) echo x86_64_defconfig;; *) echo defconfig;; esac; }
img() { case $1 in riscv) echo arch/riscv/boot/Image;; arm64) echo arch/arm64/boot/Image;; x86_64) echo arch/x86/boot/bzImage;; esac; }
ARCHS="riscv x86_64 arm64"
for a in $ARCHS; do
  O=$W/b_$a; t0=$(date +%s); ka=$(karch $a); mkdir -p $O
  make -C $S O=$O ARCH=$ka LLVM=1 $(defc $a) > $O.cfg.log 2>&1 || { echo "${a}_pre DEFCONFIG FAILED" | tee -a $LOG; continue; }
  $S/scripts/config --file $O/.config -e TRANSPARENT_HUGEPAGE
  make -C $S O=$O ARCH=$ka LLVM=1 olddefconfig >> $O.cfg.log 2>&1
  echo "${a}_pre config: $(grep -E '^CONFIG_(TRANSPARENT_HUGEPAGE|TRANSPARENT_HUGEPAGE_ALWAYS|TRANSPARENT_HUGEPAGE_MADVISE|INIT_ON_ALLOC_DEFAULT_ON|INIT_ON_FREE_DEFAULT_ON|ARM64_MTE)=' $O/.config | tr '\n' ' ')" | tee -a $LOG
  if make -C $S O=$O ARCH=$ka LLVM=1 -j20 $(basename $(img $a)) > $O.build.log 2>&1; then
    cp $O/$(img $a) $K/${a}_pre.img; cp $O/.config $K/${a}_pre.config
    echo "${a}_pre BUILD OK $(( $(date +%s)-t0 ))s" | tee -a $LOG
  else
    echo "${a}_pre BUILD FAILED $(( $(date +%s)-t0 ))s: $(grep -a -m3 -E ' error|Error ' $O.build.log | tr '\n' ' ' | cut -c1-400)" | tee -a $LOG
  fi
done
git -C $KSRC diff --binary $PARENT $FIX > $W/fix.diff
(cd $S && git apply --whitespace=nowarn $W/fix.diff) || { echo "fix diff does not apply" | tee -a $LOG; exit 1; }
for a in $ARCHS; do
  [ -f $K/${a}_pre.img ] || continue
  O=$W/b_$a; t0=$(date +%s); ka=$(karch $a)
  if make -C $S O=$O ARCH=$ka LLVM=1 -j20 $(basename $(img $a)) > $O.fix.log 2>&1; then
    cp $O/$(img $a) $K/${a}_fix.img; cp $O/.config $K/${a}_fix.config
    echo "${a}_fix BUILD OK $(( $(date +%s)-t0 ))s rebuilt=$(grep -c ' CC ' $O.fix.log)" | tee -a $LOG
  else
    echo "${a}_fix BUILD FAILED" | tee -a $LOG
  fi
done
rm -f $W/fix.diff; rm -rf $S $W/b_*
echo "end $(date '+%F %T') $(du -sh $W | cut -f1)" | tee -a $LOG
