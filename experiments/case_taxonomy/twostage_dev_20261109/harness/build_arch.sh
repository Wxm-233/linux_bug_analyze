# Full defconfig build of one revision for one architecture (criteria section 5).
#   build_arch.sh <tag> <rev> <riscv|arm64|x86_64> [trace]   -> /root/work/difftest/build/<tag>/
# arm64: debug info switched off (only speeds up the build; no effect on runtime semantics).
# trace: FUNCTION_TRACER + DYNAMIC_FTRACE on (bridge kernel only, never used for comparison).
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
tag=$1; rev=$2; arch=$3; mode=${4:-}
W=/root/work/difftest; src=$W/src/$tag; out=$W/build/$tag
case $arch in riscv) A=riscv; img=arch/riscv/boot/Image; t=Image ;; arm64) A=arm64; img=arch/arm64/boot/Image; t=Image ;;
  x86_64) A=x86; img=arch/x86/boot/bzImage; t=bzImage ;; esac
[ -f $out/$img ] && { echo "$tag already built"; exit 0; }
mkdir -p $src $out
[ -f $src/Makefile ] || git -C $KSRC archive $rev | tar -x -C $src
cd $src
make O=$out ARCH=$A LLVM=1 defconfig > $out/config.log 2>&1
if [ $arch = arm64 ]; then
  ./scripts/config --file $out/.config -d DEBUG_INFO -d DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT -d DEBUG_INFO_DWARF4 -d DEBUG_INFO_DWARF5 -e DEBUG_INFO_NONE
fi
if [ "$mode" = trace ]; then
  ./scripts/config --file $out/.config -e FTRACE -e FUNCTION_TRACER -e DYNAMIC_FTRACE
fi
make O=$out ARCH=$A LLVM=1 olddefconfig >> $out/config.log 2>&1
make O=$out ARCH=$A LLVM=1 -j20 $t > $out/build.log 2>&1 || { tail -25 $out/build.log; exit 3; }
ls -la $out/$img
rm -rf $src
find $out -name '*.o' -delete -o -name '*.a' -delete -o -name '*.ko' -delete 2>/dev/null || true
