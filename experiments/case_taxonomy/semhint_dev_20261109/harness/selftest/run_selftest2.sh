source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/semhint_dev_20261109/harness
W=/root/work/semhint/selftest; mkdir -p $W
declare -A IMG=([riscv]=$KBUILD/riscv_defconfig/arch/riscv/boot/Image [arm64]=$KBUILD/arm64_defconfig/arch/arm64/boot/Image [x86_64]=$KBUILD/x86_64_defconfig/arch/x86/boot/bzImage)
for a in riscv arm64 x86_64; do bash $H/mk_initramfs.sh $a $H/selftest/selftest_cases_$a.txt $W/$a.cpio || exit 1; done
for a in riscv arm64 x86_64; do bash $H/run_qemu.sh $a ${IMG[$a]} $W/$a.cpio $W/$a.log & done
wait
for a in riscv arm64 x86_64; do python3 $H/parse_log.py $W/$a.log > $W/$a.json; echo "$a parse rc=$?"; done
