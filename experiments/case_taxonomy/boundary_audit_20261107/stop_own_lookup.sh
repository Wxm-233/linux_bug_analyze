source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
pkill -INT -f '^python3 -B unresolved.py$' || test "$?" -eq 1
