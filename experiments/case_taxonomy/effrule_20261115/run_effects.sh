source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/effrule_20261115
python3 effects.py 2>&1 | tee effects.log
