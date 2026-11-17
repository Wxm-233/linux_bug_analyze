# Re-run the six groups with warning-level kernel messages on the console (kwarn criteria 二). Runs in WSL.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
CT=$REPO/experiments/case_taxonomy
for g in CUR A101 A310 A171 A181 B467; do
  echo "== $g"
  PAR=12 bash $CT/difftest_tools_20261111/run.sh $CT/kwarn_dev_20261111/kernels_$g.json
done
