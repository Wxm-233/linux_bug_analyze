source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
H="$REPO/experiments/case_taxonomy/semhint_dev_20261109/harness"
W=/root/work/semhint/selftest
if [[ ${1:-} == inspect ]]; then
  df -h /root/work
  for cc in riscv64-linux-gnu-gcc aarch64-linux-gnu-gcc x86_64-linux-gnu-gcc; do
    printf '\n%s\n' "$cc"
    "$cc" -dumpfullversion
    "$cc" -E -H -include asm/unistd.h -x c /dev/null -o /dev/null 2>&1
    "$cc" -dM -E -include asm/unistd.h -x c /dev/null | \
      awk '$2 ~ /^__NR_(getpid|read|write|mmap|recvmsg|close|fcntl|openat|readlinkat|fstat|lseek|eventfd2|memfd_create|getsockname|getpgid|exit_group|munmap)$/ {print}' | sort
  done
  for image in "$KBUILD/riscv_defconfig/arch/riscv/boot/Image" \
               "$KBUILD/arm64_defconfig/arch/arm64/boot/Image" \
               "$KBUILD/x86_64_defconfig/arch/x86/boot/bzImage"; do
    stat -c '%n %s bytes' "$image"
  done
  command -v cpio qemu-system-riscv64 qemu-system-aarch64 qemu-system-x86_64
  exit 0
fi
echo 'usage: bash run_selftest.sh inspect' >&2
exit 2
