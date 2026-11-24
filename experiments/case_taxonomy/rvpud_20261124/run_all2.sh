# rvpud criteria2 三: M1..M7, 3 runs each
I=/root/work/kbuild/images/65e4fd942f72
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/rvpud_20261124/run2.sh ${TAG:-main2} \
  ${I}_riscv_pfnmapdbg_-.img:riscv:M1_R0_A:A ${I}_riscv_pfnmapdbg_-.img:riscv:M2_R0_C:C ${I}_riscv_pfnmapdbg_-.img:riscv:M3_R0_D:D \
  ${I}_riscv_pfnmapdbg_rvpud-F.img:riscv:M4_RF_A:A ${I}_riscv_pfnmapdbg_rvpud-F.img:riscv:M5_RF_D:D \
  ${I}_x86_64_pfnmapdbg_-.img:x86_64:M6_X0_A:A ${I}_x86_64_pfnmapdbg_-.img:x86_64:M7_X0_D:D
