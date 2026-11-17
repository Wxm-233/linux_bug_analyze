H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/difftest_proto_20261109/harness
for a in riscv arm64 x86_64; do bash $H/mk_initramfs.sh $a || exit 1; done
mkdir -p /root/work/difftest/smoke
bash $H/run_qemu.sh riscv /root/work/boundary_build/riscv_defconfig/arch/riscv/boot/Image /root/work/difftest/smoke/riscv.log
sed -n '/@@DT BEGIN/,/@@DT END/p' /root/work/difftest/smoke/riscv.log
tail -3 /root/work/difftest/smoke/riscv.log
