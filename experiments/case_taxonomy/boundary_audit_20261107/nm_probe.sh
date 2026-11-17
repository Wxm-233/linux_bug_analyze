source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
cd /root/work/boundary_build/riscv_defconfig
llvm-nm --format=posix --print-file-name --extern-only vmlinux.a | head -20 || test "${PIPESTATUS[0]}" -eq 74
