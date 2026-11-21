source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
cd $REPO/experiments/case_taxonomy/linmap2_20261119
python3 linmap2.py selftest | tail -1
NS=$(python3 linmap2.py diag)
echo "samples: $NS"
# resumable: samples whose diag/NNN.json exists are skipped
echo $NS | tr ' ' '\n' | xargs -P 2 -I{} sh -c 'f=$(printf "diag/%03d.json" {}); [ -f "$f" ] && echo skip {} || { python3 linmap2.py diag {} > diag_{}.log 2>&1; echo done {} rc=$?; }'
python3 linmap2.py merge > merge.log 2>&1
echo merged
