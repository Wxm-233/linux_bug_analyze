#!/bin/bash
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -e
R=$REPO/experiments/case_taxonomy/lpaeqemu_20261122
W=/root/work/lpaeqemu
st=$W/stage; rm -rf $st; mkdir -p $st/proc $st/sys $st/dev $W/keep
clang --target=armv7a-linux-gnueabihf -march=armv7-a -marm -O2 -ffreestanding -nostdlib -static -fno-pic -fno-stack-protector \
  -fomit-frame-pointer -fuse-ld=lld -Wl,-e,_start -o $st/init $R/init.c
mknod -m 600 $st/dev/console c 5 1
file $st/init
(cd $st && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > $W/keep/init.cpio
ls -la $W/keep/init.cpio
