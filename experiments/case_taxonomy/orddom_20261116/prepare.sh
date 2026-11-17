# orddom criteria 二: page-size variants (defconfig + THP + page size + modules_prepare, no kernel build). WSL.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
SRC=/root/work/kbuild/pristine/df2908090cda
W=/root/work/encprobe
prep() {  # prep <name> <ARCH> <defconfig> <scripts/config args...>
  local n=$1 a=$2 dc=$3; shift 3; local o=$W/$n
  mkdir -p $o
  {
    make -C $SRC O=$o ARCH=$a LLVM=1 $dc && \
    $SRC/scripts/config --file $o/.config -e TRANSPARENT_HUGEPAGE "$@" && \
    make -C $SRC O=$o ARCH=$a LLVM=1 olddefconfig && \
    make -C $SRC O=$o ARCH=$a LLVM=1 -j4 modules_prepare
  } > $o/prepare.log 2>&1
  echo "$n rc=$? $(grep -E '^CONFIG_(ARM64_(4|16|64)K_PAGES|PPC_(4|64)K_PAGES|PAGE_SIZE_(4|16|64)KB|(4|16|64)KB_3LEVEL|TRANSPARENT_HUGEPAGE|ARCH_FORCE_MAX_ORDER)=' $o/.config | tr '\n' ' ')"
}
export -f prep; export SRC W
printf '%s\n' \
  "arm64_16k arm64 defconfig -d ARM64_4K_PAGES -e ARM64_16K_PAGES" \
  "arm64_64k arm64 defconfig -d ARM64_4K_PAGES -e ARM64_64K_PAGES" \
  "loongarch_4k loongarch defconfig -d 16KB_3LEVEL -e 4KB_3LEVEL" \
  "loongarch_64k loongarch defconfig -d 16KB_3LEVEL -e 64KB_3LEVEL" \
  "powerpc_4k powerpc ppc64le_defconfig -d PPC_64K_PAGES -e PPC_4K_PAGES" \
  "mips_16k mips 64r6el_defconfig -d PAGE_SIZE_4KB -e PAGE_SIZE_16KB" \
  "mips_64k mips 64r6el_defconfig -d PAGE_SIZE_4KB -e PAGE_SIZE_64KB" \
  | xargs -P 7 -L 1 bash -c 'prep "$@"' _
