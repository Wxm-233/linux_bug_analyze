source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -Eeuo pipefail
round="$REPO/experiments/case_taxonomy/boundary_closure_20261108"
cd "$REPO"
export PYTHONDONTWRITEBYTECODE=1
python3 "$round/prototype_batch.py" "$@"
