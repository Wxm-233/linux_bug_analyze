# s5dyn criteria 三: dbgvm plain/F5 x 3 arch + dyn plain x86_64/riscv, 3 runs each
I=/root/work/kbuild/images/df2908090cda
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s5dyn_20261116/run.sh ${TAG:-main} \
  ${I}_x86_64_dbgvm_-.img:x86_64:x86_64_dbgvm_plain:- ${I}_x86_64_dbgvm_s5dyn-F5.img:x86_64:x86_64_dbgvm_F5:- \
  ${I}_riscv_dbgvm_-.img:riscv:riscv_dbgvm_plain:- ${I}_riscv_dbgvm_s5dyn-F5.img:riscv:riscv_dbgvm_F5:- \
  ${I}_arm64_dbgvm_-.img:arm64:arm64_dbgvm_plain:- ${I}_arm64_dbgvm_s5dyn-F5.img:arm64:arm64_dbgvm_F5:- \
  ${I}_x86_64_dyn_-.img:x86_64:x86_64_dyn_plain:- ${I}_riscv_dyn_-.img:riscv:riscv_dyn_plain:-
