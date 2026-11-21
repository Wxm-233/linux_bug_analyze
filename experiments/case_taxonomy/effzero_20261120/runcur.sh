source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/effzero_20261120
mkdir -p cur
/usr/bin/time -v python3 runcur.py > cur/runcur.log 2>&1
echo "rc=$?" >> cur/runcur.log
