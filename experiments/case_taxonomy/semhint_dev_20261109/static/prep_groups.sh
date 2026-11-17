# Values, hints and cases for the listed groups (criteria 4.4-4.6, 五).   prep_groups.sh <group>...
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/semhint_dev_20261109
for g in "$@"; do
  t=${g}_pre; [ $g = CUR ] && t=CUR
  python3 $H/static/macro_values.py $g /root/work/semhint/facts/$t.json.gz | tail -3 || exit 1
  python3 $H/static/hints.py $g || exit 1
  (cd $H/gen && python3 generate.py $g) || exit 1
done
