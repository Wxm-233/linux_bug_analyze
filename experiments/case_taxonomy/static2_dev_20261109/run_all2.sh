# Run G2'/G3' cases of the listed groups on round-1 kernels, 3 times each (static2 criteria 4.4).
# Uses round-1 harness scripts read-only.   run_all2.sh <group>...   logs -> /root/work/static2/runs/<group>/
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R1=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/semhint_dev_20261109
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/static2_dev_20261109
D=/root/work/difftest/build; W=/root/work/static2
jobs=$W/jobs.$$.txt; : > $jobs
for g in "$@"; do
  for a in riscv arm64 x86_64; do bash $R1/harness/mk_initramfs.sh $a $H/gen/cases_${g}_$a.txt $W/initramfs/${g}_$a.cpio >/dev/null || exit 1; done
  mkdir -p $W/runs/$g
  if [ $g = CUR ]; then
    ks="cur_riscv:riscv:$KBUILD/riscv_defconfig/arch/riscv/boot/Image cur_arm64:arm64:$KBUILD/arm64_defconfig/arch/arm64/boot/Image cur_x86_64:x86_64:$KBUILD/x86_64_defconfig/arch/x86/boot/bzImage"
  else
    l=$(echo $g | tr A-Z a-z)
    ks="${l}_pre:riscv:$D/${g}_pre/arch/riscv/boot/Image ${l}_fix:riscv:$D/${g}_fix/arch/riscv/boot/Image ${l}_ref_arm64:arm64:$D/${g}_ref_arm64/arch/arm64/boot/Image ${l}_ref_x86_64:x86_64:$D/${g}_ref_x86_64/arch/x86/boot/bzImage"
  fi
  for k in $ks; do
    IFS=: read name arch img <<< "$k"
    for i in 1 2 3; do echo "$arch $img $W/initramfs/${g}_$arch.cpio $W/runs/$g/$name.run$i.log" >> $jobs; done
  done
done
echo "jobs: $(wc -l < $jobs)  start $(date +%T)"
xargs -P ${PAR:-10} -L 1 bash $R1/harness/run_qemu.sh < $jobs
echo "done $(date +%T)"
for g in "$@"; do for f in $W/runs/$g/*.log; do grep -q '^@@SH END' $f || echo "INCOMPLETE $f"; done; done
rm -f $jobs
