# Full riscv defconfig builds, pre-fix (fix^) and fix, for the four new samples (criteria section 3).
P=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/difftest_proto_20261109/harness
for spec in A101:2116988d5372 A310:61119394631f A171:890ba5be6335 A181:1046791390af; do
  id=${spec%%:*}; c=${spec#*:}
  for v in pre fix; do
    rev=$c; [ $v = pre ] && rev="$c^"
    s=$(date +%s); bash $P/build_kernel.sh ${id}_$v "$rev"; echo "${id}_$v rc=$? seconds=$(( $(date +%s) - s ))"
  done
done
echo ALL_DONE
