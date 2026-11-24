#!/bin/bash
# amendment 1: header-only arm64 config variants (defconfig + scripts/config + olddefconfig + make prepare)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd "$KSRC"
mk() {
  name=$1; shift
  out=/root/work/pgassert/cfg_$name
  rm -rf "$out"; mkdir -p "$out"
  make O="$out" ARCH=arm64 LLVM=1 defconfig > "$out/config.log" 2>&1
  scripts/config --file "$out/.config" "$@"
  make O="$out" ARCH=arm64 LLVM=1 olddefconfig >> "$out/config.log" 2>&1
  if make O="$out" ARCH=arm64 LLVM=1 -j20 prepare > "$out/prepare.log" 2>&1; then st=ok; else st=fail; fi
  echo "$name prepare=$st $(grep -E '^CONFIG_(PGTABLE_LEVELS|ARM64_PA_BITS|ARM64_VA_BITS|ARM64_LPA2|ARM64_4K_PAGES|ARM64_16K_PAGES|ARM64_64K_PAGES|TRANSPARENT_HUGEPAGE)=' "$out/.config" | tr '\n' ' ')"
}
mk arm64_16k -d ARM64_4K_PAGES -e ARM64_16K_PAGES
mk arm64_64k -d ARM64_4K_PAGES -e ARM64_64K_PAGES -d ARM64_PA_BITS_48 -e ARM64_PA_BITS_52
mk arm64_pa48 -d ARM64_VA_BITS_52 -e ARM64_VA_BITS_48 -d ARM64_PA_BITS_52 -e ARM64_PA_BITS_48 -d ARM64_LPA2
