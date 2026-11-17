I=/root/work/kbuild/images/df2908090cda
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s6dyn_20261116/run.sh ${TAG:-main} \
  ${I}_arm64_pg64k_-.img:pg64k_plain_force:force ${I}_arm64_pg64k_-.img:pg64k_plain_always:always \
  ${I}_arm64_pg64k_s6dyn-F6.img:pg64k_F6_force:force ${I}_arm64_dyn_-.img:dyn4k_plain_force:force
