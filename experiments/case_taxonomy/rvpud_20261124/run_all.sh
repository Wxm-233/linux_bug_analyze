# rvpud criteria 四: T1/T2/T4 on the original image, T3 on mutant F; 3 runs each
I=/root/work/kbuild/images/df2908090cda_riscv_pfnmap
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/rvpud_20261124/run.sh ${TAG:-main} \
  ${I}_-.img:T1_orig_A:A ${I}_-.img:T2_orig_C:C ${I}_rvpud-F.img:T3_fix_A:A ${I}_-.img:T4_orig_D:D
