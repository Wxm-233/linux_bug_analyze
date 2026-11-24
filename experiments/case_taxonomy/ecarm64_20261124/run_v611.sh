#!/bin/bash
# ecarm64: after the df run, list changed builds, then the v6.11 parent of 144bb0aee33a only (user 11-24: "先单跑 v6.11"), then recall.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecarm64_20261124
while pgrep -f 'ec10.py df' >/dev/null; do sleep 30; done
grep -a -E "EC4|EC5|Trace|StopIteration" logs/df.log | cut -c1-200
python3 ec10.py changed > logs/changed.log 2>&1; cat logs/changed.log
bash ../ecbuild_20261122/ensure_src.sh 4dd7724f02ab > /dev/null
python3 ec10.py parent 144bb0aee33a > logs/parent_144bb0aee33a.log 2>&1
grep -a "PARENT missing\|EC4 4dd7724f02ab \|EC4 144bb0aee33a-fixed" logs/parent_144bb0aee33a.log | cut -c1-200
python3 ec10.py recall > logs/recall.log 2>&1
grep -a "RECALL7 144bb0aee33a" logs/recall.log | cut -c1-600
python3 g12.py 4dd7724f02ab 2>&1 | grep -a comparable
echo "space $(df -h / | awk 'NR==2{print $4" free of "$2}')"
