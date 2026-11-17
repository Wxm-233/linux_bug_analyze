# Boot the current-version LoongArch kernel with the minimal init (heldout_prep criteria 三).
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/boot_test
W=/root/work/heldout/boot; mkdir -p $W/root
clang --target=loongarch64-linux-gnu -O2 -static -nostdlib -fuse-ld=lld -o $W/root/init $H/min_init.c || exit 1
(cd $W/root && echo init | cpio -o -H newc --quiet) > $W/init.cpio
K=/root/work/heldout/build/cur_loongarch
for img in $K/arch/loongarch/boot/vmlinux.efi $K/vmlinux; do
  [ -f $img ] || continue
  echo "== $img"
  timeout 180 qemu-system-loongarch64 -M virt -cpu la464 -smp 1 -m 1G -nographic -no-reboot -kernel $img -initrd $W/init.cpio -append "console=ttyS0,115200 panic=-1" < /dev/null > $W/boot_$(basename $img).log 2>&1
  echo "exit=$?"; grep -a -m3 -E "@@LA BOOT OK|Kernel panic|Linux version" $W/boot_$(basename $img).log; tail -3 $W/boot_$(basename $img).log
done
