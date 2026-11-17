# Partial riscv build of one sample's pre-fix tree (criteria section 5).
#   build_partial.sh <source_dir> <out_dir> "<dir/ dir/ ...>" [CONFIG_NAME ...]
# defconfig + the given options (=y, verified in .config), LLVM=1, build only the given directories
# (those that exist in this tree), then compile_commands.json.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
src=$1; out=$2; dirs=$3; shift 3
mkdir -p "$out"
if [ -f "$out/compile_commands.json" ] && [ -f "$out/status.txt" ]; then echo "already built: $out"; exit 0; fi
cd "$src"
make O="$out" ARCH=riscv LLVM=1 defconfig > "$out/config.log" 2>&1
for o in "$@"; do ./scripts/config --file "$out/.config" -e "$o"; done
make O="$out" ARCH=riscv LLVM=1 olddefconfig >> "$out/config.log" 2>&1
for o in "$@"; do
    grep -q "^CONFIG_$o=y" "$out/.config" || { echo "CONFIG_$o not effective" | tee "$out/failed.txt"; exit 2; }
done
targets=()
for d in $dirs; do [ -d "$src/$d" ] && targets+=("$d"); done
echo "targets: ${targets[*]}" > "$out/targets.txt"
make O="$out" ARCH=riscv LLVM=1 -j20 "${targets[@]}" > "$out/build.log" 2>&1 || { tail -n 25 "$out/build.log" > "$out/failed.txt"; exit 3; }
python3 scripts/clang-tools/gen_compile_commands.py -d "$out" -o "$out/compile_commands.json" > "$out/ccdb.log" 2>&1
echo success > "$out/status.txt"
echo "built $out (${#targets[@]} directories)"
