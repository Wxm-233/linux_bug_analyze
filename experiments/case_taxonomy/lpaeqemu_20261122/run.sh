#!/bin/bash
# lpaeqemu criteria 二: boot the arm LPAE kernel with a second RAM bank above (test) or below (control) 64GB. WSL root.
#   bash run.sh test|ctrl
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/lpaeqemu_20261122
W=/root/work/lpaeqemu
case $1 in
  test) high=0x1000000000 ;;   # 64GB: PFN >= 2^24
  ctrl) high=0x800000000 ;;    # 32GB: PFN <  2^24
  *) echo "usage: run.sh test|ctrl"; exit 1 ;;
esac
img=$W/ram_$1.img
rm -f $img; truncate -s 64G $img            # sparse: only pages the guest writes take space
timeout 300 qemu-system-arm -M virt,highmem=on,memory-backend=m0 -cpu cortex-a15 -smp 1 -m 64G \
  -object memory-backend-file,id=m0,size=64G,mem-path=$img,share=on \
  -kernel $W/keep/${K:-base}/zImage -initrd $W/keep/init.cpio \
  -append "console=ttyAMA0 panic=-1 rdinit=/init mem=1G@0x40000000 mem=512M@$high" \
  -nographic -no-reboot > $R/logs/run_${K:-base}_$1.log 2>&1
echo "exit $? ($1) image used: $(du -sh $img | cut -f1)" | tee -a $R/logs/run_${K:-base}_$1.log
rm -f $img
