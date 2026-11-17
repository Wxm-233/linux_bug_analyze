# Feasibility build 2: loongson64_defconfig with RELOCATABLE off (QEMU 8.2 direct boot test), LLVM=1.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
O=/root/work/heldout/build/cur_loongarch_norel; mkdir -p $O
s=$(date +%s)
make -C $KSRC O=$O ARCH=loongarch LLVM=1 loongson64_defconfig > $O/config.log 2>&1
$KSRC/scripts/config --file $O/.config -d RELOCATABLE -d RANDOMIZE_BASE
make -C $KSRC O=$O ARCH=loongarch LLVM=1 olddefconfig >> $O/config.log 2>&1
grep -E "^CONFIG_RELOCATABLE|^# CONFIG_RELOCATABLE|RANDOMIZE_BASE" $O/.config
make -C $KSRC O=$O ARCH=loongarch LLVM=1 -j20 vmlinux > $O/build.log 2>&1; rc=$?
echo "rc=$rc seconds=$(( $(date +%s) - s ))"; tail -3 $O/build.log
readelf -h $O/vmlinux | grep -E "Type|Entry"
W=/root/work/heldout/boot
timeout 120 qemu-system-loongarch64 -M virt -cpu la464 -smp 1 -m 1G -nographic -no-reboot -kernel $O/vmlinux -initrd $W/init.cpio -append "console=ttyS0,115200 earlycon panic=-1" < /dev/null > $W/boot_norel.log 2>&1
echo "boot exit=$?"; grep -a -m3 -E "@@LA BOOT OK|Kernel panic|Linux version" $W/boot_norel.log; tail -c 600 $W/boot_norel.log | tr -cd '\11\12\15\40-\176'
