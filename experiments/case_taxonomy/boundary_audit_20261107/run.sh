source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
cd "$REPO/experiments/case_taxonomy/boundary_audit_20261107"
exec python3 -B "$@"
