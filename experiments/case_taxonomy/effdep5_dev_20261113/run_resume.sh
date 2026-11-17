R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/effdep5_dev_20261113
echo "resume $(date "+%F %T") (previous run stopped during A387 when the session ended)" >> $R/prep.log
bash $R/prep.sh samples
