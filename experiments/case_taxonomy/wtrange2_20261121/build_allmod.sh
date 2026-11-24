#!/bin/bash
# wtrange2 criteria 1: i386 allmodconfig, WERROR off, no PAE, make -k.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
out=/root/work/wtrange2/i386_allmod
mkdir -p "$out"
cd "$KSRC"
echo "src $(git rev-parse HEAD)"
make O="$out" ARCH=i386 LLVM=1 allmodconfig > "$out/config.log" 2>&1 || { echo allmodconfig-fail; exit 1; }
scripts/config --file "$out/.config" -d WERROR -d X86_PAE -d HIGHMEM64G -e HIGHMEM4G
make O="$out" ARCH=i386 LLVM=1 olddefconfig >> "$out/config.log" 2>&1
grep -E '^CONFIG_(X86_32|X86_PAE|PHYS_ADDR_T_64BIT|WERROR|HIGHMEM4G|HIGHMEM64G)=' "$out/.config"; grep -c '=m$' "$out/.config"
df -h /root | tail -1
/usr/bin/time -v make O="$out" ARCH=i386 LLVM=1 -k -j20 > "$out/build.log" 2>&1; echo "make rc=$?"
grep -E "Elapsed" "$out/build.log"
grep -E "^make\[[0-9]+\]: \*\*\* \[" "$out/build.log" | sed -E 's/.*\[([^]]+)\].*/\1/' | sort -u > "$out/failed_targets.txt"; echo "failed targets $(wc -l < "$out/failed_targets.txt")"
python3 scripts/clang-tools/gen_compile_commands.py -d "$out" -o "$out/compile_commands.json" > "$out/cc.log" 2>&1 || { echo cc-fail; exit 1; }
echo "cc entries $(grep -c '"file"' "$out/compile_commands.json")"
du -sh "$out"; df -h /root | tail -1
echo success > "$out/status.txt"
