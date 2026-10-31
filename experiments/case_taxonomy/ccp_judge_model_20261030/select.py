"""Model judgement pilot: pick the sample (criteria.md). Hashes only; prints counts.
Main: 20 of the untouched pairs whose target is within v2's top 30. RISC-V: the 3 existing-function pairs within top 30.
Output: sample.json.
"""
from pathlib import Path
import json
import random

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
RISCV = ('46e714c7', 'b54b6003', 'd14e99bf')


def main():
    target = HERE / 'sample.json'
    if target.exists():
        raise SystemExit('preserve')
    rows = json.loads((C_DIR / 'ccp_candgen_v2_20261030' / 'v2_pool.json').read_text())['rows']
    pool = {(p['seed'], p['target']): p for p in json.loads((C_DIR / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs']}
    eligible = sorted((r['seed'], r['target']) for r in rows
                      if r['fresh'] and not r['audited'] and r['best_rank_v2'] and r['best_rank_v2'] <= 30)
    random.Random(20261031).shuffle(eligible)
    pick = lambda key, n, group: {'n': n, 'group': group, 'seed': key[0], 'target': key[1],
                                  'c_arches': pool[key]['c_arches'], 'targets': pool[key]['targets']}
    sample = [pick(k, n, 'main') for n, k in enumerate(eligible[:20], 1)]
    riscv = sorted((r['seed'], r['target']) for r in rows if r['target'].startswith(RISCV))
    sample += [pick(k, 20 + n, 'riscv') for n, k in enumerate(riscv, 1)]
    target.write_text(json.dumps({'eligible_main': len(eligible), 'sample': sample}, indent=1) + '\n')
    print('eligible', len(eligible), 'main', 20, 'riscv', len(riscv))


if __name__ == '__main__':
    main()
