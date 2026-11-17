#!/bin/bash
# Build the static /init test and its initramfs (once), then boot the given kernel (base|patched) in QEMU riscv64
# with Svnapot and save the console log under logs/. Usage: run.sh base|patched
set -euo pipefail
KIND=$1
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/work/napot_verify
mkdir -p "$HERE/logs" "$W/initramfs"
if [ ! -f "$W/init.cpio" ]; then
  riscv64-linux-gnu-gcc -static -O1 -Wall -I"$W/hdr/include" -o "$W/initramfs/init" "$HERE/napot_test.c"
  mkdir -p "$W/initramfs/proc" "$W/initramfs/sys"
  (cd "$W/initramfs" && find . | cpio -o -H newc --quiet > "$W/init.cpio")
  sha256sum "$W/initramfs/init" "$W/init.cpio"
fi
LOG="$HERE/logs/$KIND.log"
timeout 600 qemu-system-riscv64 -machine virt -cpu rv64,svnapot=on -smp 2 -m 1G -nographic -no-reboot \
  -bios default -kernel "$W/out-$KIND/arch/riscv/boot/Image" -initrd "$W/init.cpio" \
  -append "console=ttyS0 hugepagesz=64K hugepages=16 panic=-1" > "$LOG" 2>&1 || echo "qemu exit=$?"
sed -i 's/\r$//' "$LOG"
grep -E 'NAPOT-TEST|SCENARIO|RESULT|pages:|read |hugepages|Svnapot|svnapot|WARNING|BUG|Oops|panic' "$LOG" || true
