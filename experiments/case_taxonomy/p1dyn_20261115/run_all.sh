I=/root/work/kbuild/images/df2908090cda
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/p1dyn_20261115/run.sh main \
  ${I}_riscv_dyn_-.img:riscv:riscv_plain ${I}_riscv_dyn_p1dyn-F1.img:riscv:riscv_F1 ${I}_riscv_dyn_p1dyn-F2.img:riscv:riscv_F2 \
  ${I}_x86_64_dyn_-.img:x86_64:x86_64_plain ${I}_x86_64_dyn_p1dyn-F1.img:x86_64:x86_64_F1 ${I}_x86_64_dyn_p1dyn-F2.img:x86_64:x86_64_F2 \
  ${I}_arm64_dyn_-.img:arm64:arm64_plain ${I}_arm64_dyn_p1dyn-F1.img:arm64:arm64_F1 ${I}_arm64_dyn_p1dyn-F2.img:arm64:arm64_F2
