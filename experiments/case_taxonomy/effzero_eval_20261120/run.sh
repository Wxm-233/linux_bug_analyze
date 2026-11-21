source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/effzero_eval_20261120
mkdir -p sealed
python3 evalez.py run > eval.log 2>&1
echo "rc=$?" >> eval.log
