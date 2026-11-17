H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/twostage_dev_20261109/harness
s=$(date +%s); bash $H/build_arch.sh cur_riscv_trace df2908090cda riscv trace; echo "cur_riscv_trace rc=$? seconds=$(( $(date +%s) - s ))"
for spec in A101:2116988d5372 A310:61119394631f A171:890ba5be6335 A181:1046791390af B467:c625154993d0; do
  id=${spec%%:*}; c=${spec#*:}
  for a in x86_64 arm64; do
    s=$(date +%s); bash $H/build_arch.sh ${id}_ref_$a $c $a; echo "${id}_ref_$a rc=$? seconds=$(( $(date +%s) - s ))"
  done
done
df -h / | tail -1
echo ALL_DONE
