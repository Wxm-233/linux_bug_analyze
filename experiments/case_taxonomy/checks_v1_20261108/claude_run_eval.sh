# Claude 2026-11-08: wait for the closure-round config builds to finish (CPU), then run the whole evaluation.
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
LOG="$REPO/experiments/case_taxonomy/boundary_closure_20261108/claude_build_all.log"
until grep -q '^end ' "$LOG"; do sleep 30; done
cd "$REPO/experiments/case_taxonomy/checks_v1_20261108"
python3 -B selftest/verify.py > selftest/rerun.log 2>&1 || { echo "selftest failed"; exit 1; }
python3 -B eval_samples.py "$@"
