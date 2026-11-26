# layerbound criteria 三.1: allyesconfig per arch (config only), into /root/work/layerbound/avail_<arch>
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
W=/root/work/layerbound; mkdir -p $W
for a in riscv arm64 x86_64; do
  ka=$a; [ $a = x86_64 ] && ka=x86
  o=$W/avail_$a; rm -rf $o; mkdir -p $o
  make -C /root/repos/linux O=$o ARCH=$ka LLVM=1 allyesconfig > $o/log.txt 2>&1 || { echo "FAIL $a"; tail -5 $o/log.txt; }
  echo "$a symbols $(grep -cE '^(CONFIG_|# CONFIG_)' $o/.config)"
done
cd /root/repos/linux && git status -s | head -3; echo status_done
