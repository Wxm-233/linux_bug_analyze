# Regression (casemodel criteria 三): round rankprune G3r/G2r cases of group A171, new executor, each kernel once.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/casemodel_dev_20261110/harness
RP=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/rankprune_dev_20261110
W=/root/work/casemodel/regress; D=/root/work/difftest/build; mkdir -p $W
for a in riscv arm64 x86_64; do bash $H/mk_initramfs.sh $a $RP/gen/cases_A171_$a.txt $W/$a.cpio > /dev/null || exit 1; done
bash $H/run_qemu.sh riscv $D/A171_pre/arch/riscv/boot/Image $W/riscv.cpio $W/a171_pre.log &
bash $H/run_qemu.sh riscv $D/A171_fix/arch/riscv/boot/Image $W/riscv.cpio $W/a171_fix.log &
bash $H/run_qemu.sh arm64 $D/A171_ref_arm64/arch/arm64/boot/Image $W/arm64.cpio $W/a171_ref_arm64.log &
bash $H/run_qemu.sh x86_64 $D/A171_ref_x86_64/arch/x86/boot/bzImage $W/x86_64.cpio $W/a171_ref_x86_64.log &
wait
python3 $H/regress_check.py $W $RP/runs/A171
