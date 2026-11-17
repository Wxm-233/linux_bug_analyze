source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
R=$REPO/experiments/case_taxonomy/fieldhint_dev_20261111
rm -f /root/work/fieldhint/facts/B467_pre.only.json.gz
for t in CUR A101_pre A310_pre A171_pre A181_pre B467_pre; do
  [ -f /root/work/fieldhint/facts/$t.json.gz ] && { echo "$t exists"; continue; }
  bash $R/export_extract.sh $t
  python3 $R/static/facts_regress.py /root/work/fieldhint/facts/$t.json.gz /root/work/casemodel/facts/$t.json.gz --full
done
rm -rf /root/work/difftest/src/*_pre; df -h /root | tail -1
