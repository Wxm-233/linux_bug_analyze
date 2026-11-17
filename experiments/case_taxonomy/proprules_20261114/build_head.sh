# Current-version kernels (proprules criteria 四). WSL.  -> /root/work/proprules/kernels/{riscv,x86_64,arm64}_head.{img,config}
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/proprules_20261114
REV=$(git -C $KSRC rev-parse --short=12 HEAD)
W=/root/work/proprules; S=$W/src; K=$W/kernels; mkdir -p $W $K
LOG=$R/build_head.log; : > $LOG
echo "HEAD $REV $(git -C $KSRC log -1 --format=%s HEAD) start $(date '+%F %T')" | tee -a $LOG
rm -rf $S; mkdir -p $S; git -C $KSRC archive --format=tar HEAD | tar -x -C $S
karch() { case $1 in riscv) echo riscv;; arm64) echo arm64;; x86_64) echo x86;; esac; }
defc() { case $1 in x86_64) echo x86_64_defconfig;; *) echo defconfig;; esac; }
img() { case $1 in riscv) echo arch/riscv/boot/Image;; arm64) echo arch/arm64/boot/Image;; x86_64) echo arch/x86/boot/bzImage;; esac; }
for a in riscv x86_64 arm64; do
  O=$W/b_$a; t0=$(date +%s); ka=$(karch $a); mkdir -p $O
  make -C $S O=$O ARCH=$ka LLVM=1 $(defc $a) > $O.cfg.log 2>&1 || { echo "${a}_head DEFCONFIG FAILED" | tee -a $LOG; continue; }
  $S/scripts/config --file $O/.config -e TRANSPARENT_HUGEPAGE
  make -C $S O=$O ARCH=$ka LLVM=1 olddefconfig >> $O.cfg.log 2>&1
  echo "${a}_head config: $(grep -E '^CONFIG_(TRANSPARENT_HUGEPAGE|TRANSPARENT_HUGEPAGE_ALWAYS|INIT_ON_ALLOC_DEFAULT_ON|INIT_ON_FREE_DEFAULT_ON|ARM64_MTE|MEMFD_CREATE)=' $O/.config | tr '\n' ' ')" | tee -a $LOG
  if make -C $S O=$O ARCH=$ka LLVM=1 -j20 $(basename $(img $a)) > $O.build.log 2>&1; then
    cp $O/$(img $a) $K/${a}_head.img; cp $O/.config $K/${a}_head.config
    echo "${a}_head BUILD OK $(( $(date +%s)-t0 ))s" | tee -a $LOG
  else
    echo "${a}_head BUILD FAILED $(( $(date +%s)-t0 ))s: $(grep -a -m3 -E ' error|Error ' $O.build.log | tr '\n' ' ' | cut -c1-400)" | tee -a $LOG
  fi
done
rm -rf $S $W/b_*
echo "end $(date '+%F %T') $(du -sh $W | cut -f1)" | tee -a $LOG
