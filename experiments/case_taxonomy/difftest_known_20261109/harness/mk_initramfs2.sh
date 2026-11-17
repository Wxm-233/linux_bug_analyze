# Build the per-architecture initramfs with the static /init v2 (criteria section 4).
#   mk_initramfs2.sh <riscv|arm64|x86_64>  -> /root/work/difftest/initramfs2/<arch>.cpio
set -euo pipefail
arch=$1
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/difftest_known_20261109/harness
W=/root/work/difftest/initramfs2; mkdir -p $W
case $arch in
  riscv) cc=riscv64-linux-gnu-gcc ;; arm64) cc=aarch64-linux-gnu-gcc ;; x86_64) cc=x86_64-linux-gnu-gcc ;;
  *) echo "unknown arch $arch"; exit 2 ;;
esac
root=$(mktemp -d); mkdir -p $root/dev $root/proc $root/sys
$cc -static -O2 -Wall -o $root/init $H/dt_init2.c
(cd $root && find . | LC_ALL=C sort | cpio -o -H newc --quiet) > $W/$arch.cpio
sha256sum $root/init | sed "s#$root/##" > $W/$arch.init.sha256
rm -rf $root
ls -la $W/$arch.cpio
