source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
H=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/static2_dev_20261109/static
for g in "$@"; do t=${g}_pre; [ $g = CUR ] && t=CUR; python3 $H/macro_values2.py $g /root/work/static2/facts/$t.json.gz || exit 1; done
