source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
cd /root/work/boundary_build/riscv_defconfig
head -5 modules.order
file fs/btrfs/btrfs.mod drivers/usb/gadget/function/usb_f_eem.mod drivers/gpu/drm/nouveau/nouveau.mod
head -c 200 fs/btrfs/btrfs.mod
