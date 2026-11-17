# Claude 2026-11-08: run the senior's archbound collect on our v7.3-rc2 builds (read-only source; outputs under /root/work/archbound/kernel)
set -uo pipefail
cd /root/work/archbound; mkdir -p kernel
B=/root/work/boundary_build
run(){ local tag=$1 dir=$2; local t0=$(date +%s)
  ./archbound collect -p $B/$dir/compile_commands.json --root /root/repos/linux --arch $tag -j 6 --out kernel/facts.$tag.json > kernel/collect_$tag.log 2>&1
  echo "$tag exit=$? secs=$(( $(date +%s)-t0 )) errors=$(grep -c ' error: ' kernel/collect_$tag.log) fatal=$(grep -c 'fatal error' kernel/collect_$tag.log) $(tail -1 kernel/collect_$tag.log)"; }
run riscv riscv_defconfig
run x86 x86_64_defconfig
run riscv32 closure_20261108_rv32_abi
ls -la kernel/*.json
