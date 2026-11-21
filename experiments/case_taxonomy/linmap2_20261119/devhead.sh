source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/linmap2_20261119
python3 linmap2.py dev > dev.log 2>&1 &
python3 linmap2.py run df2908090cda head.json > head.log 2>&1 &
wait
echo "dev rc and head done"
grep -a -E "^(btf|zswap)" dev.log
grep -a -E "^v1|^info" head.log | cut -c1-300
