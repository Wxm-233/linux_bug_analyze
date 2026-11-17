"""Print the round-2 program facts for the items whose facts changed most (die, setup_arch, KVM_CAP_NR_VCPUS and one
R10 and one CTX more). WSL (git); no model. Output: selftest.log (stdout)."""
from pathlib import Path
import json
from facts2 import facts

HERE = Path(__file__).resolve().parent
LABELS = HERE.parent / 'llm_review_v2_dev_20261104' / 'labels3.json'

rows = {r['cand']: r for r in json.loads(LABELS.read_text(encoding='utf-8'))['rows']}
for k in (0, 27, 46, 57, 20, 51):
    print(f'--- {k} {rows[k]["snapshot"]} {rows[k]["rule"]} {rows[k]["name"]} [{rows[k]["label3"]}]')
    for f in facts(rows[k], 'loongarch'):
        print(' ', f['id'], f['text'])
