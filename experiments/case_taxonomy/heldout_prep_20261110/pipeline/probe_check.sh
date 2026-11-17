source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
P="$REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline"
TARGET=riscv BOUNDARY_POOL=existing python3 "$P/probe_check.py"
TARGET=loongarch BOUNDARY_POOL=none python3 "$P/probe_check.py"
