W=/root/work/s6dyn; I=/root/work/kbuild/images/df2908090cda_arm64_pg64k_-.img
v() { local tag=$1 smp=$2 t=$3; shift 3
  timeout ${t}s qemu-system-aarch64 -M virt -cpu max -accel tcg -nographic -no-reboot -smp $smp -m 2048M -kernel $I -initrd $W/ird/arm64.cpio \
    -append "console=ttyAMA0 panic=-1 nokaslr s6mode=force $*" < /dev/null > /tmp/s6v_$tag.log 2>&1
  echo "== $tag exit=$? BOOT=$(grep -ac '"t":"BOOT"' /tmp/s6v_$tag.log) lines=$(wc -l < /tmp/s6v_$tag.log)"; grep -a 'Run /init\|Freeing unused\|hung\|blocked for\|calling\|initcall' /tmp/s6v_$tag.log | tail -3 | cut -c1-160; tail -2 /tmp/s6v_$tag.log | cut -c1-160; }
v smp1 1 300 loglevel=7 &
v rodata 2 300 loglevel=7 rodata=off &
v long 2 500 loglevel=8 initcall_debug &
wait
