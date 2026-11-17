set -uo pipefail
cd /root/work/archbound; mkdir -p kernel/cdb_riscv
S=/mnt/c/Users/dell/AppData/Local/Temp/claude/9fd635bfbbb91193/85a3fb53-11cd-41f5-9f3f-98c9249974d0/scratchpad
python3 $S/nomd.py /root/work/boundary_build/riscv_defconfig/compile_commands.json kernel/cdb_riscv/compile_commands.json
./archbound collect -p kernel/cdb_riscv/compile_commands.json --root /root/repos/linux --arch riscv -j 4 \
   --out kernel/facts.riscv.nomd.json $(cat kernel/scope_riscv.txt) > kernel/collect_riscv_nomd.log 2>&1
echo "exit=$? err_units=$(grep -c 'Error while processing' kernel/collect_riscv_nomd.log) $(grep '^\[collect\]' kernel/collect_riscv_nomd.log)"
grep -v 'Processing file' kernel/collect_riscv_nomd.log | sed 's/[0-9]\+/N/g' | sort | uniq -c | sort -rn | head -8
