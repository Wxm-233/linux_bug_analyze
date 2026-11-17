# Layouts + vocabulary + cases for the listed groups (casemodel criteria C1-C3, 四).
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/casemodel_dev_20261110
for g in "$@"; do
  t=${g}_pre; [ $g = CUR ] && t=CUR
  python3 $H/static/layouts.py $g /root/work/casemodel/facts/$t.json.gz | tail -1 || exit 1
  cp /root/work/casemodel/layouts/$g.json $H/gen/layouts_$g.json
  python3 $H/static/vocab.py $g || exit 1
  (cd $H/gen && python3 generate_m.py $g) || exit 1
done
