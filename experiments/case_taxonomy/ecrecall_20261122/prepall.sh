source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/ecrecall_20261122
for h in $(cut -f1 pool.tsv); do python3 recall.py prep $h 2>&1 | head -1; done
