"""Labelling aid (criteria.md section 4): for every test candidate, the commits between its snapshot and the end
version df2908090cda that touch the flagged function, by llm_review_expand_20261103/evidence.py's one() (imported,
unchanged). WSL (git); no model. Usage: python3 evidence_test.py L|M   Output: evidence_L.json or evidence_M.json."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ev', HERE.parent / 'llm_review_expand_20261103' / 'evidence.py')
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def main():
    group = sys.argv[1]
    rows = json.loads((HERE / f'candidates_{group}.json').read_text(encoding='utf-8'))['rows']
    with ThreadPoolExecutor(8) as ex:
        out = list(ex.map(E.one, rows))
    (HERE / f'evidence_{group}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for r in out:
        print(r['cand'], r['snapshot'], r['name'], 'end' if r['name_at_end'] else 'GONE', len(r['commits']))
        for c in r['commits'][:12]:
            print('    ', c[:110])


if __name__ == '__main__':
    main()
