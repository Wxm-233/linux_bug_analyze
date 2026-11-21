source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/outparam_20261120
/usr/bin/time -v python3 scope.py run > scope.log 2>&1
echo "rc=$?" >> scope.log
