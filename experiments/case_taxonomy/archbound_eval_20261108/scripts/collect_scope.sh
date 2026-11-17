# Claude 2026-11-08: archbound collect restricted to the checks_v1 scope (.c only); first full run was OOM-killed at 14.6 GB.
set -uo pipefail
cd /root/work/archbound; mkdir -p kernel
B=/root/work/boundary_build; S=/mnt/c/Users/dell/AppData/Local/Temp/claude/9fd635bfbbb91193/85a3fb53-11cd-41f5-9f3f-98c9249974d0/scratchpad
run(){ local tag=$1 dir=$2 adir=$3; local t0=$(date +%s)
  python3 $S/scope_list.py $B/$dir/compile_commands.json $adir kernel/scope_$tag.txt
  /usr/bin/time -v ./archbound collect -p $B/$dir/compile_commands.json --root /root/repos/linux --arch $tag -j 4 \
     --out kernel/facts.$tag.json $(cat kernel/scope_$tag.txt) > kernel/collect_$tag.log 2>&1
  echo "$tag exit=$? secs=$(( $(date +%s)-t0 )) err_units=$(grep -c 'Error while processing' kernel/collect_$tag.log) maxrss_kb=$(grep 'Maximum resident' kernel/collect_$tag.log | awk '{print $NF}') $(grep '^\[collect\]' kernel/collect_$tag.log)"; }
run riscv riscv_defconfig riscv
run x86 x86_64_defconfig x86
run riscv32 closure_20261108_rv32_abi riscv
ls -la kernel/facts.*.json
