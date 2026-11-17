source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
python3 -B "$REPO/experiments/case_taxonomy/boundary_enum_20261106/selftest/debug.py"
