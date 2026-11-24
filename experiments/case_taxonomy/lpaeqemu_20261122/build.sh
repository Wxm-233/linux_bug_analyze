#!/bin/bash
# lpaeqemu criteria 二: arm LPAE kernel (multi_v7 + LPAE + VMSPLIT_2G + THP + DEBUG_FS + DEBUG_VM), flatmem. WSL root.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -e
R=$REPO/experiments/case_taxonomy/lpaeqemu_20261122
W=/root/work/lpaeqemu
mkdir -p $W $R/logs
cd $KSRC
[ "$(git rev-parse --short=12 HEAD)" = df2908090cda ]
MK="make O=$W/out ARCH=arm LLVM=1"
rm -rf $W/out
$MK multi_v7_defconfig > $R/logs/build.log 2>&1
scripts/config --file $W/out/.config -e ARM_LPAE -d VMSPLIT_3G -e VMSPLIT_2G -e TRANSPARENT_HUGEPAGE -e TRANSPARENT_HUGEPAGE_ALWAYS \
  -e DEBUG_FS -e DEBUG_KERNEL -e DEBUG_VM -e BLK_DEV_INITRD ${EXTRA_CFG}
$MK olddefconfig >> $R/logs/build.log 2>&1
grep -E '^CONFIG_(ARM_LPAE|VMSPLIT_2G|TRANSPARENT_HUGEPAGE|DEBUG_FS|DEBUG_VM|FLATMEM|SPARSEMEM|HIGHMEM|MIGRATION|COMPACTION|PHYS_ADDR_T_64BIT|BLK_DEV_INITRD)=' $W/out/.config | tee $R/logs/config_check.txt
start=$(date +%s)
$MK -j20 zImage >> $R/logs/build.log 2>&1
echo "build secs $(( $(date +%s) - start ))" | tee -a $R/logs/build.log
mkdir -p $W/keep/${TAG:-base}
cp $W/out/arch/arm/boot/zImage $W/out/.config $W/out/System.map $W/keep/${TAG:-base}/
cp $W/out/.config $R/kernel_${TAG:-base}.config
du -sh $W/out $W/keep; rm -rf $W/out
