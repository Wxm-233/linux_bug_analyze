#!/bin/bash
# Boot one kernel (observe|control|fixed) once in QEMU riscv64 virt with 4 harts and the bpf_test initramfs
# (criteria.md section 2). Console log: logs/<kind>.log
set -euo pipefail
KIND=$1
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/work/patchmap_verify
R=$W/rootfs-$KIND
rm -rf "$R"
mkdir -p "$R/proc" "$HERE/logs"
riscv64-linux-gnu-gcc -static -O1 -Wall -o "$R/init" "$HERE/bpf_test.c"
(cd "$R" && find . | cpio -o -H newc --quiet > "$W/initramfs-$KIND.cpio")
sha256sum "$R/init" "$W/out-$KIND/arch/riscv/boot/Image" "$W/initramfs-$KIND.cpio"
LOG="$HERE/logs/$KIND.log"
timeout 600 qemu-system-riscv64 -machine virt -smp 4 -m 1G -nographic -no-reboot -bios default \
  -kernel "$W/out-$KIND/arch/riscv/boot/Image" -initrd "$W/initramfs-$KIND.cpio" \
  -append "console=ttyS0 panic=-1" > "$LOG" 2>&1 || echo "qemu exit=$?"
sed -i 's/\r$//' "$LOG"
grep -a -E 'BPF-TEST|WARNING:|BUG:|Oops|panic|bpf_jit|Call Trace|\] (bpf|patch)' "$LOG" | head -60 || true
