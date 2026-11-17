# Boot one kernel with the arch's initramfs in QEMU (TCG), capture the serial console (criteria section 2).
#   run_qemu.sh <riscv|arm64|x86_64> <kernel image> <out log>
set -uo pipefail
arch=$1; kernel=$2; log=$3
I=/root/work/difftest/initramfs/$arch.cpio
common=(-nographic -no-reboot -smp 1 -m 512M -kernel "$kernel" -initrd "$I")
case $arch in
  riscv)  cmd=(qemu-system-riscv64 -M virt -cpu rv64,sscofpmf=true -bios default "${common[@]}" -append "console=ttyS0 panic=-1 quiet") ;;
  arm64)  cmd=(qemu-system-aarch64 -M virt -cpu max "${common[@]}" -append "console=ttyAMA0 panic=-1 quiet") ;;
  x86_64) cmd=(qemu-system-x86_64 -M q35 -cpu max "${common[@]}" -append "console=ttyS0 panic=-1 quiet") ;;
esac
timeout 600 "${cmd[@]}" < /dev/null > "$log" 2>&1
echo "exit=$? $(grep -c '^{' "$log") result lines -> $log"
