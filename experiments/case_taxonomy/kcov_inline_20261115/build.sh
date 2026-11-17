# Debug-info KCOV kernels (kcov_inline criteria 二). WSL. -> /root/work/kcov_inline/kernels/<arch>_<tag>.{img,config,vmlinux,nm}
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
R=$REPO/experiments/case_taxonomy/kcov_inline_20261115
OLD=/root/work/kcov/kernels
W=/root/work/kcov_inline; K=$W/kernels; mkdir -p $W $K
LOG=$R/build.log; : > $LOG
karch() { case $1 in riscv) echo riscv;; x86_64) echo x86;; esac; }
defc() { case $1 in x86_64) echo x86_64_defconfig;; *) echo defconfig;; esac; }
img() { case $1 in riscv) echo arch/riscv/boot/Image;; x86_64) echo arch/x86/boot/bzImage;; esac; }
for spec in head:HEAD x1pre:e7c375b18160; do
  tag=${spec%%:*}; rev=${spec##*:}; S=$W/src_$tag
  echo "$tag $rev start $(date '+%F %T')" | tee -a $LOG
  rm -rf $S; mkdir -p $S; git -C $KSRC archive --format=tar $rev | tar -x -C $S
  for a in riscv x86_64; do
    O=$W/b_${tag}_$a; t0=$(date +%s); ka=$(karch $a); mkdir -p $O
    make -C $S O=$O ARCH=$ka LLVM=1 $(defc $a) > $O.cfg.log 2>&1 || { echo "${a}_$tag DEFCONFIG FAILED" | tee -a $LOG; continue; }
    $S/scripts/config --file $O/.config -e TRANSPARENT_HUGEPAGE -e KCOV -e DEBUG_FS \
      -d DEBUG_INFO_NONE -e DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT -e DEBUG_INFO_REDUCED
    make -C $S O=$O ARCH=$ka LLVM=1 olddefconfig >> $O.cfg.log 2>&1
    echo "${a}_$tag config: $(grep -E '^CONFIG_(KCOV|DEBUG_FS|TRANSPARENT_HUGEPAGE|DEBUG_INFO[A-Z_]*)=' $O/.config | tr '\n' ' ')" | tee -a $LOG
    echo "${a}_$tag config diff vs kcov_20261115: $(diff <(grep '^CONFIG' $OLD/${a}_$tag.config | sort) <(grep '^CONFIG' $O/.config | sort) | grep '^[<>]' | tr '\n' ' ')" | tee -a $LOG
    if make -C $S O=$O ARCH=$ka LLVM=1 -j20 $(basename $(img $a)) vmlinux > $O.build.log 2>&1; then
      cp $O/$(img $a) $K/${a}_$tag.img; cp $O/.config $K/${a}_$tag.config; cp $O/vmlinux $K/${a}_$tag.vmlinux
      llvm-nm -n $O/vmlinux | grep -i ' [tw] ' > $K/${a}_$tag.nm
      if cmp -s $K/${a}_$tag.nm $OLD/${a}_$tag.nm; then same=IDENTICAL; else same="DIFFERENT($(diff $OLD/${a}_$tag.nm $K/${a}_$tag.nm | grep -c '^[<>]') lines)"; fi
      echo "${a}_$tag BUILD OK $(( $(date +%s)-t0 ))s text_syms=$(wc -l < $K/${a}_$tag.nm) nm_vs_kcov=$same" | tee -a $LOG
    else
      echo "${a}_$tag BUILD FAILED $(( $(date +%s)-t0 ))s: $(grep -a -m3 -E ' error|Error ' $O.build.log | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG
    fi
    rm -rf $O
  done
  rm -rf $S
done
echo "end $(date '+%F %T') $(du -sh $W | cut -f1)" | tee -a $LOG
