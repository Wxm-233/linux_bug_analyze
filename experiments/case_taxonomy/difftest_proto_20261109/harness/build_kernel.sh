# Full riscv defconfig build of one revision for the differential prototype (criteria section 2).
#   build_kernel.sh <tag> <rev>   -> /root/work/difftest/build/<tag>/arch/riscv/boot/Image
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
tag=$1; rev=$2
W=/root/work/difftest; src=$W/src/$tag; out=$W/build/$tag
[ -f $out/arch/riscv/boot/Image ] && { echo "$tag already built"; exit 0; }
mkdir -p $src $out
[ -f $src/Makefile ] || git -C $KSRC archive $rev | tar -x -C $src
cd $src
make O=$out ARCH=riscv LLVM=1 defconfig > $out/config.log 2>&1
make O=$out ARCH=riscv LLVM=1 -j20 Image > $out/build.log 2>&1 || { tail -25 $out/build.log; exit 3; }
ls -la $out/arch/riscv/boot/Image
rm -rf $src
