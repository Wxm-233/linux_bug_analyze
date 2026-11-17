W=/root/work/s6dyn; I=/root/work/kbuild/images/df2908090cda_arm64_pg64k_-.img
st=$W/ird/stage; aarch64-linux-gnu-gcc -static -O2 -Wall -o $st/init /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s6dyn_20261116/s6.c || exit 1
(cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/ird/arm64.cpio
v() { local tag=$1 mem=$2
  timeout 280s qemu-system-aarch64 -M virt -cpu cortex-a72 -accel tcg -nographic -no-reboot -smp 2 -m $mem -kernel $I -initrd $W/ird/arm64.cpio \
    -append "console=ttyAMA0 panic=-1 loglevel=5 nokaslr s6mode=force" < /dev/null > /tmp/s6m_$tag.log 2>&1
  echo "== $tag exit=$?"; grep -a '"t":"ENV"\|"t":"S6a"\|"t":"S6b"\|"t":"S6"\|WARNING\|xarray' /tmp/s6m_$tag.log | head -8 | cut -c1-300; }
v m2g 2048M &
v m4g 4096M &
wait
