#!/bin/bash
# ecbuild: rebuild the parent revision of each sample with mkvariants2.sh, run EC (ec6.py) at the parent and with the fix applied, clean up.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecbuild_20261122
mkdir -p logs
for h in "$@"; do
  p=$(git -C $KSRC rev-parse --short=12 $h^)
  rm -rf /root/work/ecver/$p/cfg_* /root/work/ecver/$p/status.txt /root/work/ec_cache/v6/$p /root/work/ec_cache/v6/$h-fixed
  bash mkvariants2.sh $p > logs/status_$p.txt 2>&1
  python3 ec6.py engine $p > logs/engine_$p.log 2>&1
  python3 ec6.py fixed $h > logs/fixed_$h.log 2>&1
  echo "$h parent $p builds $(grep -c ' ok ' logs/status_$p.txt) $(grep -a 'EC4' logs/engine_$p.log | grep -o '"laws": [0-9]*, "deviations": [0-9]*') $(grep -ao 'rows [0-9]*' logs/engine_$p.log | tail -1)"
  rm -rf /root/work/ecver/$p /root/work/ec_cache/v6/$h-fixed/ov
done
