source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/casemodel_dev_20261110/harness
W=/root/work/casemodel/selftest; mkdir -p $W
declare -A IMG=([riscv]=$KBUILD/riscv_defconfig/arch/riscv/boot/Image [arm64]=$KBUILD/arm64_defconfig/arch/arm64/boot/Image [x86_64]=$KBUILD/x86_64_defconfig/arch/x86/boot/bzImage)
for a in riscv arm64 x86_64; do bash $H/mk_initramfs.sh $a $H/selftest/selftest_cases_$a.txt $W/$a.cpio > /dev/null || exit 1; done
for a in riscv arm64 x86_64; do bash $H/run_qemu.sh $a ${IMG[$a]} $W/$a.cpio $W/$a.log & done
wait
for a in riscv arm64 x86_64; do echo "== $a"; grep -a -E '^\{"id"|selftest_ipc_removed|harness_error|taint_changed|@@SH END' $W/$a.log | grep -av '"selftest":' ; done
