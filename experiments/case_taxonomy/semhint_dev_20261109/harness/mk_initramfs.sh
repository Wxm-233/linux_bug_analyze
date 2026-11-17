source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
# 用法：bash mk_initramfs.sh <riscv|arm64|x86_64> <cases.txt> <输出 cpio>
set -euo pipefail
if [[ $# != 3 ]]; then
  echo 'usage: mk_initramfs.sh <riscv|arm64|x86_64> <cases.txt> <out.cpio>' >&2
  exit 2
fi
arch=$1
cases=$(realpath -e -- "$2")
output=$(realpath -m -- "$3")
H=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
case $arch in
  riscv) cc=riscv64-linux-gnu-gcc ;;
  arm64) cc=aarch64-linux-gnu-gcc ;;
  x86_64) cc=x86_64-linux-gnu-gcc ;;
  *) echo "unknown arch: $arch" >&2; exit 2 ;;
esac
mkdir -p /root/work/semhint "$(dirname -- "$output")"
stage=$(mktemp -d /root/work/semhint/initramfs.XXXXXXXX)
archive=$(mktemp "${output}.XXXXXXXX")
cleanup() {
  [[ $stage == /root/work/semhint/initramfs.* ]] && rm -rf -- "$stage"
  rm -f -- "$archive"
}
trap cleanup EXIT
mkdir -p "$stage/dev" "$stage/proc" "$stage/sys" "$stage/tmp"
"$cc" -static -O2 -Wall -o "$stage/init" "$H/sh_init.c"
chmod 0755 "$stage/init"
cp -- "$cases" "$stage/cases.txt"
(cd -- "$stage" && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --quiet) > "$archive"
mv -- "$archive" "$output"
(cd -- "$stage" && sha256sum init) > "${output%.cpio}.init.sha256"
printf 'initramfs=%s bytes=%s init_sha256=%s\n' "$output" "$(stat -c %s -- "$output")" "${output%.cpio}.init.sha256"
