W=/root/work/s6dyn; I=/root/work/kbuild/images/df2908090cda_arm64_pg64k_-.img
grep -E '^CONFIG_ARM64_VA_BITS|^CONFIG_ARM64_PA_BITS|^CONFIG_ARM64_LPA2|^CONFIG_ARM64_MTE|^CONFIG_ARM64_SME|^CONFIG_ARM64_GCS' /root/work/kbuild/images/df2908090cda_arm64_pg64k_-.config | tr '\n' ' '; echo
v() { local tag=$1 cpu=$2; shift 2
  timeout 240s qemu-system-aarch64 -M virt -cpu $cpu -accel tcg -nographic -no-reboot -smp 2 -m 2048M -kernel $I -initrd $W/ird/arm64.cpio \
    -append "console=ttyAMA0 panic=-1 loglevel=5 nokaslr s6mode=force $*" < /dev/null > /tmp/s6c_$tag.log 2>&1
  echo "== $tag exit=$? BOOT=$(grep -ac '"t":"BOOT"' /tmp/s6c_$tag.log) END=$(grep -ac '^@@END' /tmp/s6c_$tag.log)"; grep -a '"t":"S6a"\|"t":"S6b"\|WARNING' /tmp/s6c_$tag.log | head -4 | cut -c1-220; }
v a57 cortex-a57 &
v a72 cortex-a72 &
v maxnolva "max,lva=off" &
wait
