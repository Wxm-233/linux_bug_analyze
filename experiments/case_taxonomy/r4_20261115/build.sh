# R4 mutant kernels (r4 criteria 三). WSL.  -> /root/work/r4/kernels/<arch>_<M>.img
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/r4_20261115
W=/root/work/r4; S=$W/src; K=$W/kernels; mkdir -p $W $K
LOG=$R/build.log; : > $LOG
echo "HEAD $(git -C $KSRC rev-parse --short=12 HEAD) start $(date '+%F %T')" | tee -a $LOG
rm -rf $S; mkdir -p $S; git -C $KSRC archive --format=tar HEAD | tar -x -C $S
karch() { case $1 in riscv) echo riscv;; x86_64) echo x86;; esac; }
defc() { case $1 in x86_64) echo x86_64_defconfig;; *) echo defconfig;; esac; }
img() { case $1 in riscv) echo arch/riscv/boot/Image;; x86_64) echo arch/x86/boot/bzImage;; esac; }
for a in riscv x86_64; do
  O=$W/b_$a; ka=$(karch $a); mkdir -p $O; t0=$(date +%s)
  make -C $S O=$O ARCH=$ka LLVM=1 $(defc $a) > $O.cfg.log 2>&1 && $S/scripts/config --file $O/.config -e TRANSPARENT_HUGEPAGE \
    && make -C $S O=$O ARCH=$ka LLVM=1 olddefconfig >> $O.cfg.log 2>&1 \
    && make -C $S O=$O ARCH=$ka LLVM=1 -j20 $(basename $(img $a)) > $O.base.log 2>&1 \
    || { echo "${a} BASE BUILD FAILED" | tee -a $LOG; continue; }
  echo "${a} base OK $(( $(date +%s)-t0 ))s config_vs_proprules: $(diff <(grep '^CONFIG' /root/work/proprules/kernels/${a}_head.config | sort) <(grep '^CONFIG' $O/.config | sort) | grep -c '^[<>]') lines differ" | tee -a $LOG
  for m in R4a R4b; do
    t0=$(date +%s)
    python3 $R/mutate.py apply $m $a $S >> $LOG 2>&1 || { echo "${a}_$m NOT APPLIED" | tee -a $LOG; continue; }
    if make -C $S O=$O ARCH=$ka LLVM=1 -j20 $(basename $(img $a)) > $O.$m.log 2>&1; then
      cp $O/$(img $a) $K/${a}_$m.img; echo "${a}_$m BUILD OK $(( $(date +%s)-t0 ))s rebuilt=$(grep -c ' CC ' $O.$m.log) macro_redefined=$(grep -c 'macro redefined' $O.$m.log)" | tee -a $LOG
    else
      echo "${a}_$m BUILD FAILED: $(grep -a -m3 -E ' error|Error ' $O.$m.log | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG
    fi
    python3 $R/mutate.py revert $m $a $S >> $LOG 2>&1
  done
done
rm -rf $S $W/b_*
echo "end $(date '+%F %T') $(du -sh $W | cut -f1)" | tee -a $LOG
