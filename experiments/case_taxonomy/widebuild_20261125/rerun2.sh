#!/bin/bash
# widebuild: rerun layering and checks with layer_n.py (build-count fix). WSL, root.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd /root/work/layerbound5 && for f in funcs.json.gz edges.json.gz; do mv $f amend1_$f; done
cd $REPO/experiments/case_taxonomy/widebuild_20261125
echo "== $(date +%T) layer"; python3 layer5.py layer > logs/layer.log 2>&1; grep -E "^G[12] (strict|functions)|Traceback|Error" logs/layer.log | tail -4
echo "== $(date +%T) check"; python3 layer5.py check | grep -E "^G1 [0-9]|^G1 BAD|^G2|^G3"
echo "== $(date +%T) done"
