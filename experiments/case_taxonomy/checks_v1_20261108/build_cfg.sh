# Build one riscv configuration for the context check (criteria section 5, amendment 1 item 1).
#   build_cfg.sh <source_dir> <out_dir> [CONFIG_NAME ...]
# defconfig + DEBUG_ATOMIC_SLEEP + the given options (=y), verified in .config, LLVM=1, then compile_commands.json.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
src=$1; out=$2; shift 2
mkdir -p "$out"
if [ -f "$out/compile_commands.json" ] && [ -f "$out/status.txt" ]; then echo "already built: $out"; exit 0; fi
cd "$src"
make O="$out" ARCH=riscv LLVM=1 defconfig > "$out/config.log" 2>&1
opts=(DEBUG_ATOMIC_SLEEP "$@")
for o in "${opts[@]}"; do ./scripts/config --file "$out/.config" -e "$o"; done
make O="$out" ARCH=riscv LLVM=1 olddefconfig >> "$out/config.log" 2>&1
for o in "${opts[@]}"; do
    grep -q "^CONFIG_$o=y" "$out/.config" || { echo "CONFIG_$o not effective" | tee "$out/failed.txt"; exit 2; }
done
make O="$out" ARCH=riscv LLVM=1 -j20 > "$out/build.log" 2>&1 || { tail -n 20 "$out/build.log" > "$out/failed.txt"; exit 3; }
python3 scripts/clang-tools/gen_compile_commands.py -d "$out" -o "$out/compile_commands.json" > "$out/ccdb.log" 2>&1
echo success > "$out/status.txt"
echo "built $out"
