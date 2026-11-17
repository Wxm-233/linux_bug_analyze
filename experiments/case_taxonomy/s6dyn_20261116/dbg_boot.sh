W=/root/work/s6dyn; I=/root/work/kbuild/images/df2908090cda_arm64_pg64k_-.img
st=$W/ird/stage; aarch64-linux-gnu-gcc -static -O2 -Wall -o $st/init /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s6dyn_20261116/s6.c || exit 1
(cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/arm64.cpio
timeout 200s qemu-system-aarch64 -M virt -cpu max -accel tcg -nographic -no-reboot -smp 2 -m 2048M -kernel $I -initrd $W/ird/arm64.cpio \
  -append "console=ttyAMA0 panic=-1 loglevel=7 nokaslr s6mode=force" < /dev/null > /tmp/s6dbg.log 2>&1
echo "exit=$?"; grep -an '"t":\|Run /init\|Kernel panic\|WARNING\|xarray' /tmp/s6dbg.log | head; tail -5 /tmp/s6dbg.log | cut -c1-180
