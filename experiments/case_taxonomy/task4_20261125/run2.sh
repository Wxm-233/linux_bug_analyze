#!/bin/bash
# task4 amendment 1: new records (bres_w.py), covgap K2-K4 on them, round-3 engines, then task4. WSL, root.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/task4_20261125 && mkdir -p logs
python3 -m py_compile task4.py rebuild.py bres_w.py || exit 1
echo "== $(date +%T) bres"; python3 rebuild.py bres -j 12 > logs/bres.log 2>&1; grep -E "Traceback|Error" logs/bres.log | head; cut -c1-160 logs/bres.log
echo "== $(date +%T) fixtures"; python3 rebuild.py fixtures > logs/fixtures.log 2>&1; grep -E "BAD|^G2 [0-9]|Traceback" logs/fixtures.log
echo "== $(date +%T) check"; python3 rebuild.py check > logs/check.log 2>&1; grep -E "misbind total|G4 known|Traceback" logs/check.log
echo "== $(date +%T) t3"; python3 rebuild.py t3 > logs/t3.log 2>&1; grep -E "^tasks|^G1|^G3|Traceback" logs/t3.log
echo "== $(date +%T) task4"; python3 task4.py run > logs/run.log 2>&1; grep -E "^(records|XV|WT|TLB|CTX|WK|XA|G[1-5]|table)|Traceback|Error" logs/run.log | cut -c1-400
echo "== $(date +%T) done; disk free $(df -h / | tail -1 | awk '{print $4}')"
