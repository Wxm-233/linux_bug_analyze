#!/bin/bash
# widebuild amendment 1: rerun config symbols, layering and checks (line maps unchanged). WSL, root.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd /root/work/layerbound5 && for f in config_symbols.json funcs.json.gz edges.json.gz; do [ -f $f ] && mv $f run1_$f; done
cd $REPO/experiments/case_taxonomy/widebuild_20261125
echo "== $(date +%T) avail"; python3 layer5.py avail
echo "== $(date +%T) layer"; python3 layer5.py layer > logs/layer.log 2>&1; grep -E "^G[12] |Traceback|Error" logs/layer.log | tail -4
echo "== $(date +%T) check"; python3 layer5.py check
echo "== $(date +%T) done"
