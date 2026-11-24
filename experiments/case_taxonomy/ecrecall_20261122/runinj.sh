source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecrecall_20261122
for h in "$@"; do python3 recall.py run $h > logs_$h.txt 2>&1; tail -1 logs_$h.txt | cut -c1-900; done
