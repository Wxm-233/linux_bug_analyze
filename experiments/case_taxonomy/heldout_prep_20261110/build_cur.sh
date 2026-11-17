# Feasibility build (heldout_prep criteria 三): current-version loongson64_defconfig, LLVM=1.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
O=/root/work/heldout/build/cur_loongarch; mkdir -p $O
s=$(date +%s)
make -C $KSRC O=$O ARCH=loongarch LLVM=1 loongson64_defconfig > $O/config.log 2>&1 || { tail -20 $O/config.log; exit 2; }
make -C $KSRC O=$O ARCH=loongarch LLVM=1 -j20 > $O/build.log 2>&1; rc=$?
echo "rc=$rc seconds=$(( $(date +%s) - s ))"
tail -5 $O/build.log
ls -la $O/vmlinux $O/arch/loongarch/boot/ 2>&1 | head
du -sh $O
