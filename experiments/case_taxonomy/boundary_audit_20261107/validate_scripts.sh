source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107
for audit_script in run.sh claude_remerge_batch.sh validate_scripts.sh; do
    bash -n "$audit_script"
done
python3 -B - <<'PY'
import ast
from pathlib import Path
files=list(Path('.').rglob('*.py'))
for path in files:
    ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
print('PYTHON SYNTAX PASSED',len(files),'files')
PY
python3 -B remerge.py --help
