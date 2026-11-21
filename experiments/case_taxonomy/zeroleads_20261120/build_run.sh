#!/bin/bash
# zeroleads criteria: arm32 build (pre / patched) and QEMU boot test. WSL, root.
#   bash build_run.sh pre|patched
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -e
HERE=$REPO/experiments/case_taxonomy/zeroleads_20261120
W=/root/work/zeroleads
mkdir -p $W $HERE/logs
MK="make -C $W/src O=$W/out ARCH=arm LLVM=1"
if [ "$1" = pre ]; then
  rm -rf $W/src $W/out
  mkdir -p $W/src
  git -C $KSRC archive df2908090cda | tar -x -C $W/src
  cp $HERE/zl_pooltest.c $W/src/lib/
  echo 'obj-y += zl_pooltest.o' >> $W/src/lib/Makefile
  $MK multi_v7_defconfig > $HERE/logs/build_pre.log 2>&1
elif [ "$1" = patched ]; then
  f=$W/src/arch/arm/mm/dma-mapping.c
  grep -q "zeroleads patch" $f || python3 - "$f" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = "\t\tptr = (void *)val;\n\t}\n\n\treturn ptr;\n}"
assert s.count(old) == 1, "anchor not unique"
s = s.replace(old, "\t\tptr = (void *)val;\n\t\tmemset(ptr, 0, size); /* zeroleads patch */\n\t}\n\n\treturn ptr;\n}")
open(p, "w").write(s)
PY
fi
start=$(date +%s)
$MK -j20 zImage >> $HERE/logs/build_$1.log 2>&1
echo "build $1 secs $(( $(date +%s) - start ))" >> $HERE/logs/build_$1.log
cp $W/out/arch/arm/boot/zImage $W/zImage_$1
timeout 180 qemu-system-arm -M virt -cpu cortex-a15 -m 512 -kernel $W/zImage_$1 \
  -append "console=ttyAMA0 panic=-1" -nographic -no-reboot > $HERE/logs/boot_$1.log 2>&1 || true
grep -a "ZLTEST" $HERE/logs/boot_$1.log | sed 's/^\[[ 0-9.]*\] //' > $HERE/logs/result_$1.txt || true
cat $HERE/logs/result_$1.txt
