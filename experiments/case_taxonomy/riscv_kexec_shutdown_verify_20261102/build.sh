#!/bin/bash
# Build the observation (observe) or control kernel for riscv64 (plan.md). Sources from git archive; the repository is
# not touched. Usage: build.sh observe|control
set -euo pipefail
KIND=$1
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/work/kexec_verify
SRC=$W/src-$KIND
OUT=$W/out-$KIND
if [ ! -d "$SRC" ]; then
  mkdir -p "$SRC"
  git -C /root/repos/linux archive df2908090cda | tar -x -C "$SRC"
  patch -d "$SRC" -p1 < "$HERE/$KIND.patch"
fi
export ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu-
make -C "$SRC" O="$OUT" defconfig
"$SRC/scripts/config" --file "$OUT/.config" -e KEXEC_FILE -e HOTPLUG_CPU -e PROVE_LOCKING -e DEBUG_ATOMIC_SLEEP
make -C "$SRC" O="$OUT" olddefconfig
grep -E '^CONFIG_(KEXEC|KEXEC_FILE|KEXEC_CORE|HOTPLUG_CPU|PROVE_LOCKING|DEBUG_ATOMIC_SLEEP|SMP)=' "$OUT/.config"
make -C "$SRC" O="$OUT" -j20 Image
sha256sum "$OUT/arch/riscv/boot/Image"
