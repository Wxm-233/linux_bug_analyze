set -uo pipefail
cd /root/work/archbound/_fix
for a in x86 riscv; do sed "s#/home/zzzrrll/cross_arch_fuzz/tool/_fix#$PWD#g" cc.$a.json > ours.cc.$a.json; mkdir -p cdb_$a; cp ours.cc.$a.json cdb_$a/compile_commands.json; done
for a in x86 riscv; do ../archbound collect -p cdb_$a/compile_commands.json --root $PWD --arch $a --out ours.f.$a.json 2>&1 | tail -2; done
../archbound analyze --facts ours.f.x86.json,ours.f.riscv.json --report ours.r.txt --points ours.p.json 2>&1 | tail -3
diff <(grep -v '^$' r.txt) <(grep -v '^$' ours.r.txt) && echo "REPORT IDENTICAL to r.txt"
cat ours.p.json | head -c 800; echo; echo ---; cat p.json | head -c 800
