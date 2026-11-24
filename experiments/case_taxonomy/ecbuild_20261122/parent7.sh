#!/bin/bash
# parent6.sh with the 11-22 space rule: keep header variants and EC caches, drop only the source copy (re-export with ensure_src.sh, ~11 s);
# report free space after each sample.
#   bash parent7.sh <fix hash>...   -> keeps /root/work/ecver/<parent>/cfg_* and /root/work/ec_cache/v6/{<parent>,<hash>-fixed}
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
  rm -rf /root/work/ecver/$p/src
  echo "space $(df -h / | awk 'NR==2{print $4" free of "$2}') ecver $(du -sh /root/work/ecver | cut -f1)"
done
