# Boot the current-version LoongArch kernel through EDK2 firmware (Debian qemu-efi-loongarch64 2025.02-8+deb13u1).
# QEMU 8.2 cannot pass an EFI kernel with -kernel, so the kernel and initrd sit on a vvfat ESP and
# the UEFI shell runs startup.nsh.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/boot_test
W=/root/work/heldout/boot; mkdir -p $W/root $W/esp
FW=/root/work/heldout/fw/usr/share/qemu-efi-loongarch64/QEMU_EFI.fd
clang --target=loongarch64-linux-gnu -O2 -static -nostdlib -fuse-ld=lld -o $W/root/init $H/min_init.c || exit 1
(cd $W/root && echo init | cpio -o -H newc --quiet) > $W/esp/init.cpio
K=/root/work/heldout/build/cur_loongarch
cp $K/arch/loongarch/boot/vmlinux.efi $W/esp/vmlinux.efi
printf 'fs0:\r\nvmlinux.efi console=ttyS0,115200 panic=-1 initrd=\init.cpio\r\n' > $W/esp/startup.nsh
# QEMU 8.2's virt machine has no pflash and a 4 MiB -bios window; the image's data ends below 2 MiB.
head -c 4194304 $FW > $W/QEMU_EFI_4M.fd
L=$W/boot_fw.log
s=$(date +%s)
timeout 300 qemu-system-loongarch64 -M virt -cpu la464 -smp 1 -m 1G -nographic -no-reboot \
  -bios $W/QEMU_EFI_4M.fd \
  -drive file=fat:rw:$W/esp,format=raw,if=none,id=d0 -device virtio-blk-pci,drive=d0 \
  < /dev/null > $L 2>&1
echo "exit=$? secs=$(( $(date +%s) - s ))"
grep -a -m5 -E "@@LA BOOT OK|Kernel panic|Linux version|Run /init" $L; echo ---; tail -6 $L | cut -c1-200
