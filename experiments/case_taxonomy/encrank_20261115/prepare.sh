# encrank criteria 二: defconfig + options + modules_prepare per arch (no full build). WSL.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
SRC=/root/work/kbuild/pristine/df2908090cda
W=/root/work/encprobe; mkdir -p $W
OPTS="SWAP MIGRATION NUMA COMPACTION TRANSPARENT_HUGEPAGE MEMORY_HOTPLUG MEMORY_HOTREMOVE ZONE_DEVICE DEVICE_PRIVATE USERFAULTFD CHECKPOINT_RESTORE MEM_SOFT_DIRTY"
prep() {  # prep <name> <ARCH> <defconfig>
  local n=$1 a=$2 dc=$3 o=$W/$1
  mkdir -p $o
  {
    make -C $SRC O=$o ARCH=$a LLVM=1 $dc && \
    $SRC/scripts/config --file $o/.config $(for x in $OPTS; do printf -- "-e %s " $x; done) && \
    make -C $SRC O=$o ARCH=$a LLVM=1 olddefconfig && \
    make -C $SRC O=$o ARCH=$a LLVM=1 -j4 modules_prepare
  } > $o/prepare.log 2>&1
  echo "$n rc=$? $(for x in $OPTS PTE_MARKER_UFFD_WP HAVE_ARCH_USERFAULTFD_WP HAVE_ARCH_SOFT_DIRTY ARCH_HAS_PMD_SOFTLEAVES; do grep -q "^CONFIG_$x=y" $o/.config && printf '%s ' $x; done)"
}
export -f prep; export SRC W OPTS
printf '%s\n' "x86_64 x86_64 x86_64_defconfig" "arm64 arm64 defconfig" "riscv riscv defconfig" "loongarch loongarch defconfig" \
  "powerpc powerpc ppc64le_defconfig" "s390 s390 defconfig" "arm arm multi_v7_defconfig" "mips mips 64r6el_defconfig" \
  | xargs -P 8 -L 1 bash -c 'prep "$@"' _
du -sh $W
