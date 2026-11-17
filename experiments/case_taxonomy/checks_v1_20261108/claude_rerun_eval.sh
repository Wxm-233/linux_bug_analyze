# Claude 2026-11-08: rerun after amendment 2 (extractor chdir fix, counter fix, clean-parse guard).
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -uo pipefail
cd "$REPO/experiments/case_taxonomy/checks_v1_20261108"
python3 -B selftest/verify.py > selftest/rerun_after_fix.log 2>&1 || { echo "selftest failed"; tail -30 selftest/rerun_after_fix.log; exit 1; }
echo "selftest passed"
[ "${1:-}" = "selftest-only" ] && exit 0
# (the one-time rm -rf of the invalid run-1 caches was done on 2026-11-08 and removed so reruns resume)
python3 -B eval_samples.py
