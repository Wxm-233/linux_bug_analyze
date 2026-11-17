# Restore source trees (round-1 prep_trees.sh, read-only reuse) and run extract3.py on 6 trees (casemodel criteria 三).
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/casemodel_dev_20261110/static
bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/semhint_dev_20261109/static/prep_trees.sh A101 A310 A171 A181 B467 | tail -7
mkdir -p /root/work/casemodel/facts
for t in A101_pre A310_pre A171_pre A181_pre B467_pre CUR; do
  if [ $t = CUR ]; then cc=$KBUILD/riscv_defconfig/compile_commands.json; root=/root/repos/linux
  else cc=/root/work/semhint/cc/$t.json; root=/root/work/difftest/src/$t; fi
  s=$(date +%s)
  python3 $H/extract3.py $cc $root /root/work/casemodel/facts/$t.json.gz --jobs 14 2>&1 | tail -1
  echo "$t rc=$? seconds=$(( $(date +%s) - s ))"
done
df -h / | tail -1
echo ALL_DONE
