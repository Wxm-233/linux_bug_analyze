#!/bin/bash
# amendment 2: ppc64le radix-only / hash-only variants
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd "$KSRC"
mk() {
  name=$1; shift
  out=/root/work/swapsym/cfg_$name
  rm -rf "$out"; mkdir -p "$out"
  make O="$out" ARCH=powerpc LLVM=1 powernv_defconfig > "$out/config.log" 2>&1
  scripts/config --file "$out/.config" "$@"
  make O="$out" ARCH=powerpc LLVM=1 olddefconfig >> "$out/config.log" 2>&1
  if ! make O="$out" ARCH=powerpc LLVM=1 -j20 prepare > "$out/prepare.log" 2>&1; then echo "$name prepare=fail"; return; fi
  if ! make O="$out" ARCH=powerpc LLVM=1 -j20 mm/memory.o > "$out/memory.log" 2>&1; then echo "$name memory.o=fail $(grep -m2 -i error $out/memory.log | tr '\n' ' ' | cut -c1-300)"; return; fi
  echo "$name ok $(grep -E '^(# )?CONFIG_(PPC_64S_HASH_MMU|PPC_RADIX_MMU)[= ]' "$out/.config" | tr '\n' ' ')"
}
mk ppc64le_radix -d PPC_64S_HASH_MMU
mk ppc64le_hash -d PPC_RADIX_MMU
