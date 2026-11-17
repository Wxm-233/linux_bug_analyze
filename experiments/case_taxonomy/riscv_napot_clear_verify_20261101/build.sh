#!/bin/bash
# Build the unmodified range-end kernel (base) or the gate-removed control (patched) for riscv64.
# Usage: build.sh base|patched. Sources are extracted with git archive; /root/repos/linux is not touched.
set -euo pipefail
KIND=$1
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/work/napot_verify
SRC=$W/src-$KIND
OUT=$W/out-$KIND
mkdir -p "$W"
if [ ! -d "$SRC" ]; then
  mkdir -p "$SRC"
  git -C /root/repos/linux archive df2908090cda | tar -x -C "$SRC"
  if [ "$KIND" = patched ]; then
    patch -d "$SRC" -p1 < "$HERE/control.patch"
  fi
fi
export ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu-
make -C "$SRC" O="$OUT" defconfig
"$SRC/scripts/config" --file "$OUT/.config" -e USERFAULTFD -e HUGETLBFS -e RISCV_ISA_SVNAPOT
make -C "$SRC" O="$OUT" olddefconfig
grep -E '^CONFIG_(USERFAULTFD|HUGETLBFS|HUGETLB_PAGE|RISCV_ISA_SVNAPOT|PTE_MARKER_UFFD_WP|MIGRATION)=' "$OUT/.config"
make -C "$SRC" O="$OUT" -j20 Image
if [ "$KIND" = base ]; then
  make -C "$SRC" O="$OUT" headers_install INSTALL_HDR_PATH="$W/hdr"
fi
sha256sum "$OUT/arch/riscv/boot/Image"
