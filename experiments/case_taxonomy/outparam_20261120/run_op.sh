source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/outparam_20261120
python3 outparam.py selftest > selftest.log 2>&1
/usr/bin/time -v python3 outparam.py run > op.log 2>&1
echo "rc=$?" >> op.log
