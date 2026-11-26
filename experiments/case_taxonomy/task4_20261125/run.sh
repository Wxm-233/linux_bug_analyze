#!/bin/bash
# task4: WSL, root
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/task4_20261125 && mkdir -p logs
echo "== $(date +%T) run"; python3 task4.py run > logs/run.log 2>&1; grep -E "^(records|XV|WT|TLB|CTX|WK|XA|G[1-5]|table)|Traceback|Error" logs/run.log | cut -c1-300
echo "== $(date +%T) done"
