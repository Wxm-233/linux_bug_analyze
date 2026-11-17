# Calibration run (diverse criteria 二.2, unified load address): candidates on current-version riscv/arm64/x86_64, once each, executor v2.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/diverse_dev_20261110
X=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/casemodel_dev_20261110/harness
M=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/mix_dev_20261110/harness
W=/root/work/diverse/calib; mkdir -p $W
declare -A IMG=([riscv]=$KBUILD/riscv_defconfig/arch/riscv/boot/Image [arm64]=$KBUILD/arm64_defconfig/arch/arm64/boot/Image [x86_64]=$KBUILD/x86_64_defconfig/arch/x86/boot/bzImage)
for a in riscv arm64 x86_64; do bash $M/mk_initramfs.sh $a $H/gen/cases_calib_$a.txt $W/$a.cpio > /dev/null || exit 1; done
for a in riscv arm64 x86_64; do bash $X/run_qemu.sh $a ${IMG[$a]} $W/$a.cpio $W/$a.log & done
wait
for a in riscv arm64 x86_64; do grep -c '^@@SH END' $W/$a.log; done
