source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 TARGET=riscv BOUNDARY_POOL=existing
P="$REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline"
for s in extract3 hints4 macro_values macro_values2 layouts vocab rank; do
    python3 "$P/$s.py" --help > "$P/tests/help_$s.txt"
done
python3 "$P/vocab.py" CUR --facts /root/work/casemodel/facts/CUR.json.gz --values /root/work/static2/values/CUR.json --out "$P/regression/vocab_CUR.json"
python3 - "$P" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
a=json.loads((p/'regression/vocab_CUR.json').read_text())
b=json.loads((p.parents[1]/'casemodel_dev_20261110/gen/vocab_CUR.json').read_text())
assert a==b
(p/'tests/api_result.json').write_text(json.dumps({'help_scripts':7,'vocab_cli_equal':True}))
print('7 个 CLI --help 正常；vocab CLI 全字段相同')
PY
