# Same as boot_fw.sh, but hands kernel, initrd and command line to the firmware with -kernel/-initrd/-append.
W=/root/work/heldout/boot
L=$W/boot_fw_kernel.log
s=$(date +%s)
timeout 300 qemu-system-loongarch64 -M virt -cpu la464 -smp 1 -m 1G -nographic -no-reboot \
  -bios $W/QEMU_EFI_4M.fd -kernel $W/esp/vmlinux.efi -initrd $W/esp/init.cpio \
  -append "console=ttyS0,115200 panic=-1" < /dev/null > $L 2>&1
echo "exit=$? secs=$(( $(date +%s) - s ))"
grep -a -m5 -E "@@LA BOOT OK|Kernel panic|Linux version|Run /init" $L; echo ---; tail -3 $L | cut -c1-200
