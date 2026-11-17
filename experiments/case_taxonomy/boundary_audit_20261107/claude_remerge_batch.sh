source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107
audit_arch="${1:?usage: claude_remerge_batch.sh riscv|arm64|x86_64 [units_per_batch]}"
audit_limit="${2:-128}"
exec python3 -B remerge.py "$audit_arch" --limit "$audit_limit"
