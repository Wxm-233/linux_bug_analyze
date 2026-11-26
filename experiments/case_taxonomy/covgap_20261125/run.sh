#!/bin/bash
# covgap criteria 一.3 steps 2-7 (after build.sh). WSL, root. Stops at the first failing must-pass gate.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/covgap_20261125
W=/root/work/covgap
echo "== $(date +%T) avail"; python3 covgap.py avail | tee logs/avail.log | grep -E "^K0|Traceback|Error"
grep -q "^K0 PASS" logs/avail.log || { echo "K0 FAIL, stop"; exit 1; }
for b in riscv x86_64 arm64 arm powerpc; do
  echo "== $(date +%T) pp $b"; python3 covgap.py pp $b -j 10 > logs/pp_$b.log 2>&1; grep -E "done|Traceback|Error" logs/pp_$b.log | tail -2
done
echo "== $(date +%T) layer"; python3 covgap.py layer > logs/layer.log 2>&1; grep -E "Traceback|Error" logs/layer.log | head
echo "== $(date +%T) K1"; python3 g1_c.py > logs/g1.log 2>&1; grep -E "BAD|^G1 [0-9]|Traceback" logs/g1.log
echo "== $(date +%T) K2"; python3 covgap.py fixtures > logs/fixtures.log 2>&1; grep -E "BAD|^G2 [0-9]|Traceback" logs/fixtures.log
echo "== $(date +%T) bres"; python3 covgap.py bres -j 12 > logs/bres.log 2>&1; grep -E "Traceback|Error" logs/bres.log | head; cut -c1-200 logs/bres.log
echo "== $(date +%T) check"; python3 check_c.py > logs/check.log 2>&1; grep -E "misbind total|G4 known|Traceback" logs/check.log
echo "== $(date +%T) task3"; python3 covgap.py task3 > logs/task3.log 2>&1; grep -E "^tasks|^G1|^G3|Traceback" logs/task3.log
echo "== $(date +%T) compare"; python3 compare.py > logs/compare.log 2>&1; grep -E "^R1|^R3|Traceback" logs/compare.log
echo "== $(date +%T) done; disk free $(df -h / | tail -1 | awk '{print $4}')"
