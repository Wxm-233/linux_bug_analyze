#!/bin/bash
# Build one of the three kernels of criteria.md section 1 (observe|control|fixed) for riscv64 from df2908090cda via
# git archive; the repository is not touched. Stops before compiling when the config does not match the table.
set -euo pipefail
KIND=$1
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/work/patchmap_verify
SRC=$W/src-$KIND
OUT=$W/out-$KIND
if [ ! -d "$SRC" ]; then
  mkdir -p "$SRC"
  git -C /root/repos/linux archive df2908090cda | tar -x -C "$SRC"
  if [ "$KIND" = fixed ]; then
    patch -d "$SRC" -p1 < "$HERE/fixed.patch"
  fi
fi
export ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu-
make -C "$SRC" O="$OUT" defconfig > /dev/null
if [ "$KIND" = control ]; then
  "$SRC/scripts/config" --file "$OUT/.config" -e BPF_JIT
else
  "$SRC/scripts/config" --file "$OUT/.config" -e BPF_JIT -d MODULES
fi
make -C "$SRC" O="$OUT" olddefconfig > /dev/null
grep -E '^(# )?CONFIG_(MODULES|STRICT_MODULE_RWX|EXECMEM|BPF_JIT|BPF_SYSCALL)[= ]' "$OUT/.config" | tee "$HERE/logs/config-$KIND.txt"
want_mod=$([ "$KIND" = control ] && echo y || echo n)
if [ "$want_mod" = y ]; then
  grep -q '^CONFIG_MODULES=y' "$OUT/.config" && grep -q '^CONFIG_STRICT_MODULE_RWX=y' "$OUT/.config"
else
  ! grep -q '^CONFIG_MODULES=y' "$OUT/.config" && ! grep -q '^CONFIG_STRICT_MODULE_RWX=y' "$OUT/.config"
fi
grep -q '^CONFIG_BPF_JIT=y' "$OUT/.config" && grep -q '^CONFIG_EXECMEM=y' "$OUT/.config" && grep -q '^CONFIG_BPF_SYSCALL=y' "$OUT/.config"
make -C "$SRC" O="$OUT" -j20 Image > "$W/build-$KIND.log" 2>&1
tail -3 "$W/build-$KIND.log"
sha256sum "$OUT/arch/riscv/boot/Image"
