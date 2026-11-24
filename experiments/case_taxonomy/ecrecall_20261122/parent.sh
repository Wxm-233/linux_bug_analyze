#!/bin/bash
# ecrecall amendment 1: parent-revision method for each sample hash given: variants, EC at the parent, fix forward, evaluate, clean up.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecrecall_20261122
mkdir -p logs
for h in "$@"; do
  p=$(git -C $KSRC rev-parse --short=12 $h^)
  [ -f /root/work/ecver/$p/status.txt ] || bash mkvariants.sh $p > logs/variants_$p.log 2>&1
  cp /root/work/ecver/$p/status.txt logs/status_$p.txt
  full=$(git -C $KSRC rev-parse $p)
  [ -f /root/work/ec_cache/v/$p/$full.json ] || python3 ec4.py engine $p > logs/engine_$p.log 2>&1
  python3 ec4.py fixed $h > logs/fixed_$h.log 2>&1
  python3 ec4.py eval $h 2>&1 | tail -1
  [ -n "$KEEP" ] || rm -rf /root/work/ecver/$p/src /root/work/ec_cache/v/$h-fixed/ov
done
