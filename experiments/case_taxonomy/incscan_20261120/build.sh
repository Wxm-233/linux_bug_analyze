#!/bin/bash
# incscan 判据第一节：新版本源码用 git archive 导出（不动 /root/repos/linux 工作树），
# 照 boundary_enum_20261106/build.sh 的命令构建三个 defconfig，并生成编译数据库。
#   bash build.sh <NEW 完整 SHA>
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
NEW=$1
base=/root/work/incscan
src=$base/src
mkdir -p "$base/build"
clang --version > "$base/clang_version.txt"
if [ "$(cat "$base/src.done" 2>/dev/null)" != "$NEW" ]; then
    rm -rf "$src"; mkdir -p "$src"
    git -C "$KSRC" archive "$NEW" | tar -x -C "$src" || { echo "archive failed"; exit 1; }
    echo "$NEW" > "$base/src.done"
fi
for arch in riscv arm64 x86_64; do
    out="$base/build/${arch}_defconfig"
    [ "$(cat "$out/status.txt" 2>/dev/null)" = success ] && continue
    mkdir -p "$out"
    echo "$(date '+%F %T') $arch defconfig"
    make -C "$src" O="$out" ARCH="$arch" LLVM=1 defconfig > "$out/config.log" 2>&1 || { echo defconfig-fail > "$out/status.txt"; continue; }
    echo "$(date '+%F %T') $arch build"
    /usr/bin/time -v make -C "$src" O="$out" ARCH="$arch" LLVM=1 -j20 > "$out/build.log" 2>&1 || { echo build-fail > "$out/status.txt"; echo "$arch build failed"; continue; }
    python3 "$src/scripts/clang-tools/gen_compile_commands.py" -d "$out" -o "$out/compile_commands.json" > "$out/compile_commands.log" 2>&1 \
        || { echo cc-fail > "$out/status.txt"; continue; }
    sha256sum "$out/.config" > "$out/config.sha256"
    echo success > "$out/status.txt"
    echo "$(date '+%F %T') $arch done"
done
for arch in riscv arm64 x86_64; do echo "$arch $(cat "$base/build/${arch}_defconfig/status.txt")"; done
