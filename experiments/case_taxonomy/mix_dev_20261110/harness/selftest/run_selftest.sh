# casemodel executor self-test (19 cases, expected.md) with the unified load address (mix criteria 二).
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/mix_dev_20261110/harness
S=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/casemodel_dev_20261110/harness
W=/root/work/mix/selftest; mkdir -p $W
declare -A IMG=([riscv]=$KBUILD/riscv_defconfig/arch/riscv/boot/Image [arm64]=$KBUILD/arm64_defconfig/arch/arm64/boot/Image [x86_64]=$KBUILD/x86_64_defconfig/arch/x86/boot/bzImage)
for a in riscv arm64 x86_64; do bash $H/mk_initramfs.sh $a $S/selftest/selftest_cases_$a.txt $W/$a.cpio > /dev/null || exit 1; done
st=$(mktemp -d); (cd $st && cpio -id --quiet < $W/riscv.cpio && riscv64-linux-gnu-readelf -lW init | grep -m1 LOAD); rm -rf $st
for a in riscv arm64 x86_64; do bash $S/run_qemu.sh $a ${IMG[$a]} $W/$a.cpio $W/$a.log & done
wait
for a in riscv arm64 x86_64; do echo "== $a"; grep -a -E '^\{"id"|taint_changed|@@SH END|harness_error' $W/$a.log | sed 's/,"t":-1//' | tr '\n' ' ' | cut -c1-2500; echo; grep -a selftest_ipc_removed $W/$a.log | grep -a '"n":[1-9]' | tr '\n' ' '; echo; done
