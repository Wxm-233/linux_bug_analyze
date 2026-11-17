# Run the six groups with the default tools (budget criteria 二). Runs in WSL. Resumable: a group whose logs exist is skipped.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
CT=$REPO/experiments/case_taxonomy; R=$CT/fieldhint_dev_20261111
for g in CUR A101 A310 A171 A181 B467; do
  [ -d $R/runs/$g ] && [ $(ls $R/runs/$g | wc -l) -ge 9 ] && { echo "== $g skipped"; continue; }
  echo "== $g $(date +%T)"
  PAR=12 bash $CT/difftest_tools_20261111/run.sh $R/kernels_$g.json
done
