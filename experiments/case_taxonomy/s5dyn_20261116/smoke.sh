I=/root/work/kbuild/images/df2908090cda
RUNS=1 TAG=smoke bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s5dyn_20261116/run.sh smoke \
  ${I}_x86_64_dbgvm_-.img:x86_64:x86_64_dbgvm_plain:- ${I}_riscv_dbgvm_-.img:riscv:riscv_dbgvm_plain:-
