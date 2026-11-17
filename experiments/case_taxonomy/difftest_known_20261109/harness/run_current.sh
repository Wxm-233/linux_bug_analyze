H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/difftest_known_20261109/harness
for a in riscv arm64 x86_64; do bash $H/mk_initramfs2.sh $a || exit 1; done
B=/root/work/boundary_build
bash $H/run_set2.sh all cur_riscv=riscv:$B/riscv_defconfig/arch/riscv/boot/Image \
  cur_arm64=arm64:$B/arm64_defconfig/arch/arm64/boot/Image cur_x86_64=x86_64:$B/x86_64_defconfig/arch/x86/boot/bzImage \
  b467_pre=riscv:/root/work/difftest/build/B467_pre/arch/riscv/boot/Image b467_fix=riscv:/root/work/difftest/build/B467_fix/arch/riscv/boot/Image
