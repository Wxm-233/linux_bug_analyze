#!/bin/bash
# lpaeinv criteria 二: arm LPAE kernel = round-6 nohighpte config + DEBUG_VM_PGTABLE, from a git-archive copy (KSRC untouched). WSL root.
#   TAG=inv bash build.sh            (experiment)
#   TAG=ctrl PATCH=<file> bash build.sh   (control variant, only if Q2 shows anomalies)
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -e
R=$REPO/experiments/case_taxonomy/lpaeinv_20261122
W=/root/work/lpaeinv
TAG=${TAG:-inv}
mkdir -p $W $R/logs
rm -rf $W/src $W/out
mkdir -p $W/src
git -C $KSRC archive df2908090cda | tar -x -C $W/src
cd $W/src
# the only source change: let arm LPAE opt in to the generic page-table self test
sed -i 's/^\tselect HAVE_ARCH_TRANSPARENT_HUGEPAGE if ARM_LPAE$/&\n\tselect ARCH_HAS_DEBUG_VM_PGTABLE if ARM_LPAE/' arch/arm/Kconfig
grep -n "ARCH_HAS_DEBUG_VM_PGTABLE" arch/arm/Kconfig | tee $R/logs/kconfig_${TAG}.txt
[ -n "$PATCH" ] && patch -p1 < $PATCH | tee -a $R/logs/kconfig_${TAG}.txt
MK="make O=$W/out ARCH=arm LLVM=1"
cp $REPO/experiments/case_taxonomy/lpaeqemu_20261122/kernel_nohighpte.config /tmp/lpaeinv_base.config
mkdir -p $W/out; cp /tmp/lpaeinv_base.config $W/out/.config
scripts/config --file $W/out/.config -e DEBUG_VM_PGTABLE
$MK olddefconfig > $R/logs/build_${TAG}.log 2>&1
grep -E '^CONFIG_(ARM_LPAE|TRANSPARENT_HUGEPAGE|TRANSPARENT_HUGEPAGE_ALWAYS|DEBUG_VM|DEBUG_VM_PGTABLE|ARCH_HAS_DEBUG_VM_PGTABLE|HIGHPTE|SMP|FLATMEM|DEBUG_FS)=' $W/out/.config | tee $R/logs/config_check_${TAG}.txt
start=$(date +%s)
$MK -j20 zImage >> $R/logs/build_${TAG}.log 2>&1
echo "build secs $(( $(date +%s) - start ))" | tee -a $R/logs/build_${TAG}.log
mkdir -p $W/keep/$TAG
cp $W/out/arch/arm/boot/zImage $W/out/.config $W/out/System.map $W/keep/$TAG/
cp $W/out/.config $R/kernel_${TAG}.config
cd /; du -sh $W/out $W/src $W/keep; rm -rf $W/out $W/src
