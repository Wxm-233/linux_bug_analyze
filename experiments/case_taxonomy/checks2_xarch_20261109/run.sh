source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
cd "$REPO/experiments/case_taxonomy/checks2_xarch_20261109"
exec python3 -B "$@"
