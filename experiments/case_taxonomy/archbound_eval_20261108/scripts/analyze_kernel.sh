set -uo pipefail
cd /root/work/archbound/kernel
/usr/bin/time -v ../archbound analyze --facts facts.x86.json,facts.riscv.json,facts.riscv32.json --report report.txt --json report.json --points points.json > analyze.log 2>&1
echo "exit=$? maxrss_kb=$(grep 'Maximum resident' analyze.log | awk '{print $NF}')"
grep -E '^\[(analyze|points)\]' analyze.log | tail -4
python3 -c "import json;d=json.load(open('points.json'));print(json.dumps(d['count'],indent=0))"
grep -nE '^\[[0-9]' report.txt
