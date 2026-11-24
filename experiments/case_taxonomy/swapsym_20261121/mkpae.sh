#!/bin/bash
# criteria 一: header-only i386 PAE variant (i386_defconfig + X86_PAE, olddefconfig, make prepare)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd "$KSRC"
out=/root/work/swapsym/cfg_i386_pae
rm -rf "$out"; mkdir -p "$out"
make O="$out" ARCH=i386 LLVM=1 i386_defconfig > "$out/config.log" 2>&1
scripts/config --file "$out/.config" -e X86_PAE
make O="$out" ARCH=i386 LLVM=1 olddefconfig >> "$out/config.log" 2>&1
if make O="$out" ARCH=i386 LLVM=1 -j20 prepare > "$out/prepare.log" 2>&1; then st=ok; else st=fail; fi
echo "i386_pae prepare=$st $(grep -E '^CONFIG_(X86_PAE|PGTABLE_LEVELS|PHYS_ADDR_T_64BIT|SWAP|MIGRATION|MEMORY_FAILURE|DEVICE_PRIVATE)=' "$out/.config" | tr '\n' ' ')"
du -sh "$out"
