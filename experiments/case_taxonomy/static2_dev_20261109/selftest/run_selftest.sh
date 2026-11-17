# Self-test of extract2.py + hints2.py on the synthetic tree (criteria 三).
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
S=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/static2_dev_20261109/selftest
W=/root/work/static2/selftest; mkdir -p $W
T=$S/tree
python3 - <<PY
import json
T="$T"
cc=[{"directory":T,"file":f"{T}/{f}","arguments":["clang","-c","-I",f"{T}/include","-I",f"{T}/arch/riscv/include",f"{T}/{f}","-o","/dev/null"]} for f in ("kernel/sys.c","arch/riscv/kernel/impl.c")]
json.dump(cc,open("$W/cc.json","w"))
json.dump({"riscv":{"ARCH_LIM":100},"arm64":{"ARCH_LIM":200},"x86_64":{"ARCH_LIM":300}},open("$W/values.json","w"))
PY
python3 $S/../static/extract2.py $W/cc.json $T $W/facts.json.gz --jobs 2
for c in base I1 I2 I4 I1,I2 I1,I2,I3,I4; do python3 $S/../static/hints2.py $W/facts.json.gz $W/values.json $c $W/hints_$c.json > /dev/null; done
python3 $S/check_selftest.py $W
