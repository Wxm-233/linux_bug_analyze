"""v2 evaluator must give identical results (all fields incl. reasons) to v1 on every saved v1 input."""
from pathlib import Path
from collections import Counter
import json
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
from linux_bug_analyze import contract_protocol as v1  # noqa: E402
from linux_bug_analyze import contract_protocol_v2 as v2  # noqa: E402


def items(o):
    if isinstance(o, dict):
        if {'contract', 'ledger', 'record'} <= set(o):
            yield o
            return
        for v in o.values():
            yield from items(v)
    elif isinstance(o, list):
        for v in o:
            yield from items(v)


def main():
    target = HERE / 'v2_on_v1_regression.json'
    if target.exists():
        raise SystemExit('preserve')
    counts, diffs = Counter(), []
    for path in sorted((INNER / 'experiments').rglob('*.json')):
        if HERE in path.parents or path.stat().st_size > 60_000_000:
            continue
        try:
            obj = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        for it in items(obj):
            syn = it['record'].get('basis') == 'synthetic' or it['ledger'].get('basis') == 'synthetic'
            for allow in sorted({False, syn}):
                a = v1.evaluate_contract(it['contract'], it['ledger'], it['record'], allow_synthetic=allow)
                b = v2.evaluate_contract(it['contract'], it['ledger'], it['record'], allow_synthetic=allow)
                counts['evaluations'] += 1
                if a != b:
                    diffs.append({'file': path.relative_to(INNER).as_posix(), 'id': it['contract'].get('id'), 'v1': a, 'v2': b})
    out = {'evaluations': counts['evaluations'], 'differences': len(diffs), 'examples': diffs[:5]}
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'evaluations': out['evaluations'], 'differences': out['differences']}))


if __name__ == '__main__':
    main()
