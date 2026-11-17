source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
# 用法：bash run_qemu.sh <arch> <内核镜像> <initramfs> <日志>
set -uo pipefail
if [[ $# != 4 ]]; then
  echo 'usage: run_qemu.sh <riscv|loongarch|arm64|x86_64> <kernel> <initramfs> <log>' >&2
  exit 2
fi
arch=$1; kernel=$2; initramfs=$3; log=$4
[[ -r $kernel && -r $initramfs ]] || { echo 'kernel/initramfs is not readable' >&2; exit 2; }
mkdir -p -- "$(dirname -- "$log")"
common=(-accel tcg -nographic -no-reboot -smp 1 -m 512M -kernel "$kernel" -initrd "$initramfs")
case $arch in
  riscv) cmd=(qemu-system-riscv64 -M virt -cpu rv64,sscofpmf=true -bios default "${common[@]}" -append 'console=ttyS0 panic=-1 quiet') ;;
  # QEMU 8.2 needs EDK2 firmware and at least 1G of RAM for LoongArch (the others keep 512M); LA_FW is the 4 MiB-truncated Debian QEMU_EFI.fd (boot_test/boot_fw.sh).
  loongarch) cmd=(qemu-system-loongarch64 -M virt -cpu la464 -bios "${LA_FW:-/root/work/heldout/boot/QEMU_EFI_4M.fd}" "${common[@]}" -m 1G -append 'console=ttyS0,115200 panic=-1 quiet') ;;
  arm64) cmd=(qemu-system-aarch64 -M virt -cpu max "${common[@]}" -append 'console=ttyAMA0 panic=-1 quiet') ;;
  x86_64) cmd=(qemu-system-x86_64 -M q35 -cpu max "${common[@]}" -append 'console=ttyS0 panic=-1 quiet') ;;
  *) echo "unknown arch: $arch" >&2; exit 2 ;;
esac
timeout --kill-after=10s 3600s "${cmd[@]}" < /dev/null > "$log" 2>&1
rc=$?
lines=$(awk '/^\{/ {n++} END {print n+0}' "$log")
printf 'exit=%d json_lines=%s log=%s\n' "$rc" "$lines" "$log"
exit "$rc"
