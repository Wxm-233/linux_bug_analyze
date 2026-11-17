#!/bin/bash
# Build the initramfs for a kernel (observe|control) and boot it once in QEMU riscv64 with 4 harts; the first kernel
# kexecs into the same Image (plan.md). Console log: logs/<kind>.log
set -euo pipefail
KIND=$1
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/work/kexec_verify
R=$W/rootfs-$KIND
rm -rf "$R" "$W/init2-$KIND"
mkdir -p "$HERE/logs" "$R/proc" "$W/init2-$KIND/proc"
riscv64-linux-gnu-gcc -static -O1 -Wall -o "$R/init" "$HERE/kexec_test.c"
cp "$R/init" "$W/init2-$KIND/init"
(cd "$W/init2-$KIND" && find . | cpio -o -H newc --quiet > "$R/init2.cpio")
cp "$W/out-$KIND/arch/riscv/boot/Image" "$R/Image"
(cd "$R" && find . | cpio -o -H newc --quiet > "$W/initramfs-$KIND.cpio")
sha256sum "$R/init" "$R/Image" "$W/initramfs-$KIND.cpio"
LOG="$HERE/logs/$KIND.log"
timeout 600 qemu-system-riscv64 -machine virt -smp 4 -m 1G -nographic -no-reboot -bios default \
  -kernel "$W/out-$KIND/arch/riscv/boot/Image" -initrd "$W/initramfs-$KIND.cpio" \
  -append "console=ttyS0 panic=-1" > "$LOG" 2>&1 || echo "qemu exit=$?"
sed -i 's/\r$//' "$LOG"
grep -a -E 'KEXEC-|Starting new kernel|BUG:|WARNING:|lockdep|possible|Oops|panic|Kernel command line' "$LOG" | head -40 || true
