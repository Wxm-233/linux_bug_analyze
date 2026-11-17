# s4dyn criteria 三: 24 runs (arm64 plain/F2/F4 x MGLRU on/off, x86_64/riscv plain x MGLRU on) x 3
I=/root/work/kbuild/images/df2908090cda
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/s4dyn_20261116/run.sh ${TAG:-main} \
  ${I}_arm64_mglru_-.img:arm64:arm64_plain:1 ${I}_arm64_mglru_-.img:arm64:arm64_plain:0 \
  ${I}_arm64_mglru_p1dyn-F2.img:arm64:arm64_F2:1 ${I}_arm64_mglru_p1dyn-F2.img:arm64:arm64_F2:0 \
  ${I}_arm64_mglru_s4dyn-F4.img:arm64:arm64_F4:1 ${I}_arm64_mglru_s4dyn-F4.img:arm64:arm64_F4:0 \
  ${I}_x86_64_mglru_-.img:x86_64:x86_64_plain:1 ${I}_riscv_mglru_-.img:riscv:riscv_plain:1
