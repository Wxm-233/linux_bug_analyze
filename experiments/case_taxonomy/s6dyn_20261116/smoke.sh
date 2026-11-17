I=/root/work/kbuild/images/df2908090cda
RUNS=1 bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s6dyn_20261116/run.sh smoke \
  ${I}_arm64_pg64k_-.img:pg64k_plain_force:force ${I}_arm64_dyn_-.img:dyn4k_plain_force:force
