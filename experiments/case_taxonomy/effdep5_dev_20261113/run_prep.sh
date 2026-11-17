R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/effdep5_dev_20261113
echo "start $(date "+%F %T")" >> $R/prep.log
bash $R/prep.sh cur riscv
bash $R/prep.sh samples
