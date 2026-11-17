# widthtrunc criteria 二: 32-bit dirs (defconfig + modules_prepare, no kernel build). WSL.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
SRC=/root/work/kbuild/pristine/df2908090cda
W=/root/work/encprobe
prep() {  # prep <name> <ARCH> <defconfig>
  local n=$1 a=$2 dc=$3 o=$W/$1
  mkdir -p $o
  { make -C $SRC O=$o ARCH=$a LLVM=1 $dc && make -C $SRC O=$o ARCH=$a LLVM=1 -j4 modules_prepare; } > $o/prepare.log 2>&1
  echo "$n rc=$? $(grep -E '^CONFIG_(64BIT|32BIT|X86_32|PHYS_ADDR_T_64BIT|ARCH_DMA_ADDR_T_64BIT)=' $o/.config | tr '\n' ' ')"
}
export -f prep; export SRC W
printf '%s\n' "i386 x86 i386_defconfig" "riscv32 riscv rv32_defconfig" "mips32 mips 32r2el_defconfig" | xargs -P 3 -L 1 bash -c 'prep "$@"' _
