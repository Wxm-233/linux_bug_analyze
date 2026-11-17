source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 TARGET=riscv BOUNDARY_POOL=existing
P="$REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline"
python3 "$P/regress.py" audit
python3 "$P/finish.py"
