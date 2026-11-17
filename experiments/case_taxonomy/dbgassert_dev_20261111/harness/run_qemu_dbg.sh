source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
# (dbgassert: copy of casemodel_dev_20261110/harness/run_qemu.sh; only change: quiet -> loglevel=5, timeout 7200s)
# 用法：bash run_qemu_dbg.sh <arch> <内核镜像> <initramfs> <日志>
set -uo pipefail
if [[ $# != 4 ]]; then
  echo 'usage: run_qemu.sh <riscv|arm64|x86_64> <kernel> <initramfs> <log>' >&2
  exit 2
fi
arch=$1; kernel=$2; initramfs=$3; log=$4
[[ -r $kernel && -r $initramfs ]] || { echo 'kernel/initramfs is not readable' >&2; exit 2; }
mkdir -p -- "$(dirname -- "$log")"
common=(-accel tcg -nographic -no-reboot -smp 1 -m 512M -kernel "$kernel" -initrd "$initramfs")
case $arch in
  riscv) cmd=(qemu-system-riscv64 -M virt -cpu rv64,sscofpmf=true -bios default "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5') ;;
  arm64) cmd=(qemu-system-aarch64 -M virt -cpu max "${common[@]}" -append 'console=ttyAMA0 panic=-1 loglevel=5') ;;
  x86_64) cmd=(qemu-system-x86_64 -M q35 -cpu max "${common[@]}" -append 'console=ttyS0 panic=-1 loglevel=5') ;;
  *) echo "unknown arch: $arch" >&2; exit 2 ;;
esac
timeout --kill-after=10s 7200s "${cmd[@]}" < /dev/null > "$log" 2>&1
rc=$?
lines=$(awk '/^\{/ {n++} END {print n+0}' "$log")
printf 'exit=%d json_lines=%s log=%s\n' "$rc" "$lines" "$log"
exit "$rc"
