source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/linmap2_20261119
/usr/bin/time -v python3 linmap2.py diag 11 > diag_11.log 2> time_11.log
echo rc=$?
grep -E "Maximum resident|Elapsed" time_11.log
ls diag
