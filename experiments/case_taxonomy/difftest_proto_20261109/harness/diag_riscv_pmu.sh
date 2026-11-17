# diagnosis only (not part of the comparison): riscv boot messages about the PMU
#   diag_riscv_pmu.sh [extra -cpu options, e.g. ",sscofpmf=true"]
I=/root/work/difftest/initramfs/riscv.cpio
K=/root/work/boundary_build/riscv_defconfig/arch/riscv/boot/Image
timeout 300 qemu-system-riscv64 -M virt -cpu "rv64$1" -bios default -nographic -no-reboot -smp 1 -m 512M \
  -kernel "$K" -initrd "$I" -append "console=ttyS0 panic=-1 loglevel=7" < /dev/null > /tmp/diag_riscv.log 2>&1
tr -d '\000' < /tmp/diag_riscv.log | grep -aiE "pmu|perf|sscof|counter|riscv: ISA|hw_cycles|breakpoint" | head -25
