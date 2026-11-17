source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
CT=$REPO/experiments/case_taxonomy; L=$CT/locate_dev_20261111
export TARGET=riscv PYTHONPATH=$CT/heldout_prep_20261110/pipeline PYTHONDONTWRITEBYTECODE=1
for g in CUR A101 A310 A171 A181 B467; do t=${g}_pre; [ $g = CUR ] && t=CUR
  python3 $L/static_index.py $g /root/work/fieldhint/facts/$t.json.gz /root/work/static2/values/$g.json \
     $CT/fieldhint2_dev_20261111/static/fieldvocab_$g.json $L/index/$g.json 2>&1 | tail -1
done
