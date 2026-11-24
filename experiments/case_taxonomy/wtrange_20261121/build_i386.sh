#!/bin/bash
# criteria 一: the only new build of this round. Same commands as boundary_enum_20261106/build.sh, ARCH=i386 defconfig.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
out=/root/work/wtrange/i386
mkdir -p "$out"
cd "$KSRC"
echo "src $(git rev-parse HEAD)"
make O="$out" ARCH=i386 LLVM=1 i386_defconfig > "$out/config.log" 2>&1 || { echo defconfig-fail; exit 1; }
grep -E '^CONFIG_(X86_32|X86_PAE|PHYS_ADDR_T_64BIT|64BIT)=' "$out/.config"
/usr/bin/time -v make O="$out" ARCH=i386 LLVM=1 -j20 > "$out/build.log" 2>&1 || { echo build-fail; tail -20 "$out/build.log"; exit 1; }
python3 scripts/clang-tools/gen_compile_commands.py -d "$out" -o "$out/compile_commands.json" > "$out/cc.log" 2>&1 || { echo cc-fail; exit 1; }
echo "cc entries $(grep -c '"file"' "$out/compile_commands.json")"
grep -E "Elapsed" "$out/build.log"
echo success > "$out/status.txt"
