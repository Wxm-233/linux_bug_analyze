#!/bin/bash
# Archive pinned sources, configure (default / NR_CPUS=64) and build three sparc64 objects + .i per variant.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=/root/repos/linux
CACHE=/root/.cache/linux-bug-analyze/sparc-identity-objects-20261027
OUT="$HERE/attempt1"
[ -e "$OUT" ] && { echo "preserve attempt1"; exit 1; }
mkdir -p "$OUT" "$CACHE"
declare -A REV=([parent]=95706e717c4f55ca62025c151451ccc28863d085 [fixed]=98937707fea8375e8acea0aaa0b68a956dd52719)
MAKEARGS=(ARCH=sparc64 CROSS_COMPILE=sparc64-linux-gnu- -j20)
TARGETS=(arch/sparc/kernel/prom_64.o arch/sparc/kernel/setup_64.o arch/sparc/kernel/smp_64.o
         arch/sparc/kernel/prom_64.i arch/sparc/kernel/setup_64.i arch/sparc/kernel/smp_64.i)
{
echo "start $(date -Is)"
sparc64-linux-gnu-gcc --version | head -1
for ver in parent fixed; do
  SRC="$CACHE/$ver/linux"
  if [ ! -d "$SRC" ]; then
    mkdir -p "$SRC" && git -C "$REPO" archive "${REV[$ver]}" | tar -x -C "$SRC"
    echo "archive $ver rc=$?"
  fi
  for cfg in default nr64; do
    B="$CACHE/build/$ver-$cfg"; L="$OUT/$ver-$cfg"; mkdir -p "$B" "$L"
    t0=$(date +%s)
    make -C "$SRC" O="$B" "${MAKEARGS[@]}" sparc64_defconfig > "$L/defconfig.log" 2>&1; echo "$ver-$cfg defconfig rc=$?"
    if [ "$cfg" = nr64 ]; then
      "$SRC/scripts/config" --file "$B/.config" --set-val NR_CPUS 64
      make -C "$SRC" O="$B" "${MAKEARGS[@]}" olddefconfig > "$L/olddefconfig.log" 2>&1; echo "$ver-$cfg olddefconfig rc=$?"
    fi
    cp "$B/.config" "$L/config"
    make -C "$SRC" O="$B" "${MAKEARGS[@]}" "${TARGETS[@]}" > "$L/build.log" 2>&1; rc=$?
    echo "$ver-$cfg build rc=$rc seconds=$(( $(date +%s) - t0 ))"
    for t in "${TARGETS[@]}"; do
      [ -f "$B/$t" ] && cp "$B/$t" "$L/$(basename "$t")"
      c="$B/$(dirname "$t")/.$(basename "$t").cmd"; [ -f "$c" ] && cp "$c" "$L/"
    done
    grep -E '^(CONFIG_NR_CPUS|CONFIG_SMP|CONFIG_64BIT|CONFIG_FORCE_NR_CPUS|CONFIG_DEBUG_PER_CPU_MAPS|# CONFIG_FORCE_NR_CPUS|# CONFIG_DEBUG_PER_CPU_MAPS)' "$B/.config" | sed "s/^/$ver-$cfg /"
  done
done
echo "end $(date -Is)"
} > "$OUT/build_receipt.txt" 2>&1
(cd "$OUT" && find . -type f \( -name '*.o' -o -name '*.i' -o -name config \) -exec sha256sum {} + | sort -k2 > SHA256SUMS)
cat "$OUT/build_receipt.txt"
