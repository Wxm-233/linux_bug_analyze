#!/bin/bash
# widebuild criteria 二.2/二.3/三: config symbols, preprocessing line maps, layering and checks on the five builds. WSL, root.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/widebuild_20261125
echo "== $(date +%T) avail"; python3 layer5.py avail
for b in riscv x86_64 arm64 arm powerpc; do
  echo "== $(date +%T) pp $b"; python3 layer5.py pp $b -j 10 2>&1 | grep -E "done|Traceback|Error"
done
echo "== $(date +%T) layer"; python3 layer5.py layer > logs/layer.log 2>&1; grep -E "^G[123]|Traceback|Error" logs/layer.log | head -40
echo "== $(date +%T) check"; python3 layer5.py check
echo "== $(date +%T) done; disk free $(df -h / | tail -1 | awk '{print $4}')"
