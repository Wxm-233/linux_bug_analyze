#!/bin/bash
set -Eeuo pipefail
base=/root/work/boundary_build
src=/root/repos/linux
arch=preflight
stage=preflight
trap 'rc=$?; printf "%s %s %s\n" "$arch" "$stage" "$rc" > "$base/failed.txt"; exit "$rc"' ERR
cd "$src"
git rev-parse HEAD > "$base/source_head.txt"
git status --porcelain=v1 > "$base/source_status_before.txt"
clang --version > "$base/clang_version.txt"
for arch in riscv arm64 x86_64; do
    out="$base/${arch}_defconfig"
    mkdir -p "$out"
    stage=defconfig
    printf '%s %s\n' "$arch" "$stage" > "$base/progress.txt"
    make O="$out" ARCH="$arch" LLVM=1 defconfig > "$out/config.log" 2>&1
    stage=build
    printf '%s %s\n' "$arch" "$stage" > "$base/progress.txt"
    make O="$out" ARCH="$arch" LLVM=1 -j20 > "$out/build.log" 2>&1
    stage=compile_commands
    python3 scripts/clang-tools/gen_compile_commands.py -d "$out" -o "$out/compile_commands.json" > "$out/compile_commands.log" 2>&1
    sha256sum "$out/.config" > "$out/config.sha256"
    printf 'success\n' > "$out/status.txt"
done
git status --porcelain=v1 > "$base/source_status_after.txt"
printf 'success\n' > "$base/completed.txt"
