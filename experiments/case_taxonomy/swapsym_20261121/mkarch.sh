#!/bin/bash
# amendment 1: header-only variants for more architectures + one mm/memory.o compile for the compile command
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd "$KSRC"
mk() {
  name=$1; arch=$2; cfg=$3; shift 3
  out=/root/work/swapsym/cfg_$name
  rm -rf "$out"; mkdir -p "$out"
  extra=""; [ "$arch" = um ] && extra="SUBARCH=x86_64"
  if ! make O="$out" ARCH=$arch $extra LLVM=1 $cfg > "$out/config.log" 2>&1; then echo "$name config=fail $(tail -2 $out/config.log | tr '\n' ' ')"; return; fi
  if [ $# -gt 0 ]; then scripts/config --file "$out/.config" "$@"; make O="$out" ARCH=$arch $extra LLVM=1 olddefconfig >> "$out/config.log" 2>&1; fi
  if ! make O="$out" ARCH=$arch $extra LLVM=1 -j20 prepare > "$out/prepare.log" 2>&1; then echo "$name prepare=fail $(grep -m2 -i 'error' $out/prepare.log | tr '\n' ' ' | cut -c1-300)"; return; fi
  if ! make O="$out" ARCH=$arch $extra LLVM=1 -j20 mm/memory.o > "$out/memory.log" 2>&1; then echo "$name memory.o=fail $(grep -m2 -i 'error' $out/memory.log | tr '\n' ' ' | cut -c1-300)"; return; fi
  echo "$name ok $(grep -E '^CONFIG_(64BIT|PGTABLE_LEVELS|SWAP|MIGRATION|PTE_64BIT|PHYS_ADDR_T_64BIT|ARM_LPAE|XPA|PPC_BOOK3S_64|PPC_BOOK3E_64|44x|PPC_8xx)=' "$out/.config" | tr '\n' ' ') $(du -sh $out | cut -f1)"
}
mk ppc64le powerpc powernv_defconfig
mk ppc64e powerpc corenet64_smp_defconfig
mk ppc32s powerpc pmac32_defconfig
mk ppc44x powerpc ppc44x_defconfig
mk ppc8xx powerpc mpc885_ads_defconfig
mk s390 s390 defconfig
mk loongarch loongarch defconfig
mk mips32 mips malta_defconfig
mk mips32xpa mips maltaup_xpa_defconfig
mk mips64 mips 64r6el_defconfig
mk arm arm multi_v7_defconfig
mk arm_lpae arm multi_v7_defconfig -e ARM_LPAE
mk hexagon hexagon defconfig
mk um um defconfig
mk sparc64 sparc sparc64_defconfig
