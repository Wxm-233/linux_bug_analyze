source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/commitmode_20261117
for e in P1 XV ORD WT; do ( /usr/bin/time -f "$e maxrss_kb=%M wall=%e" python3 engines.py $e df2908090cda 2>&1 | tail -3 ) & done; wait
