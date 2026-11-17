# Run the listed samples' pre/fix riscv kernels 3 times each into runs/all.   run_ids.sh A101 A310 ...
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/difftest_known_20261109/harness
D=/root/work/difftest/build
specs=()
for id in "$@"; do for v in pre fix; do
  specs+=("$(echo $id | tr A-Z a-z)_$v=riscv:$D/${id}_$v/arch/riscv/boot/Image")
done; done
bash $H/run_set2.sh all "${specs[@]}"
