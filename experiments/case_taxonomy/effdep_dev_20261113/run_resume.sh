# resume after stop point: CUR riscv, then remaining samples
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/effdep_dev_20261113
echo "resume $(date "+%F %T")" >> $R/prep.log
bash $R/prep.sh cur riscv
bash $R/prep.sh samples
