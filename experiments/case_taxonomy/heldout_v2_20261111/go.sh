# Current-version dry run, then the first batch (heldout_v2). Runs in WSL.
V=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_v2_20261111
bash $V/cur_dry.sh > $V/logs/cur_dry.log 2>&1 || { echo "CUR dry run FAILED, batch not started" | tee -a $V/logs/batch.log; exit 1; }
bash $V/run_batch.sh $(cat $V/data/batch1.txt)
