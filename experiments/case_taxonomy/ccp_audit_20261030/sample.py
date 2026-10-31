"""Draw the 30-pair audit sample (criteria.md). Writes sample_30.json with hashes and targets only (no coverage fields)."""
from pathlib import Path
import json
import random

HERE = Path(__file__).resolve().parent


def main():
    target = HERE / 'sample_30.json'
    if target.exists():
        raise SystemExit('preserve')
    pairs = [p for p in json.loads((HERE.parent / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs'] if not p['overlap_commit']]
    pairs.sort(key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(pairs)
    sample = [{'n': i + 1, 'seed': p['seed'], 'target': p['target'], 'c_arches': p['c_arches'], 'targets': p['targets']} for i, p in enumerate(pairs[:30])]
    target.write_text(json.dumps({'from': len(pairs), 'sample': sample}, indent=1) + '\n')
    print('fresh', len(pairs), 'sampled', len(sample))


if __name__ == '__main__':
    main()
