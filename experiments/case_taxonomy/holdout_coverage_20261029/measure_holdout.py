"""Held-out coverage (registration.md): B3 structural correspondence vs interface users on the 22 P1'' held-out T. WSL; no model calls.
Reuses p1pp_coverage_20261029/measure_coverage.py unchanged. Output: holdout_coverage.json. Prints the summary only.
"""
from pathlib import Path
import json
import math
import statistics
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'p1pp_coverage_20261029'))
import measure_coverage as M  # noqa: E402

S, P = M.S, M.P


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def main():
    target = HERE / 'holdout_coverage.json'
    if target.exists():
        raise SystemExit('preserve')
    pool = json.loads((C / 'p1pp_design_20261029' / 'holdout_pool.json').read_text())['usable']
    rows = []
    for n, f in enumerate(pool, 1):
        pair = {'seed': f['seed'], 'target': f['target'], 't_targets': f['xarch_targets']}
        s_files = S.seed_files(pair['seed'])
        s_rels = {S.rel(x) for x in s_files if S.rel(x)}
        uni = S.universe(P.tree_files(pair['seed']), s_files)
        texts = P.read_files(pair['seed'], uni)
        b3, gids = M.b3_full(pair, uni, s_rels, texts), M.generic_ids(pair)
        api = M.api_full(uni, texts, gids)
        tg = {tuple(x) for x in pair['t_targets']}
        cov = lambda cands: any(c in tg for c in cands)
        rows.append({'n': n, 'b3_20': cov(b3[:20]), 'b3_40': cov(b3[:40]), 'b3_all': cov(b3), 'api_20': cov(api[:20]), 'api_40': cov(api[:40]),
                     'api_all': cov(api), 'union_20_20': cov(b3[:20] + api[:20]), 'union_all': cov(b3 + api),
                     'b3_pool': len(b3), 'api_pool': len(api), 'generic_ids': len(gids)})
        print(n, flush=True)
    N = len(rows)
    keys = ['b3_20', 'b3_40', 'b3_all', 'api_20', 'api_40', 'api_all', 'union_20_20', 'union_all']
    covered = {k: sum(r[k] for r in rows) for k in keys}
    miss = [r for r in rows if not r['b3_20']]
    added = sum(r['api_20'] for r in miss)
    pool_stat = lambda k: {'median': statistics.median(r[k] for r in rows), 'max': max(r[k] for r in rows), 'zero': sum(r[k] == 0 for r in rows)}
    reading = {
        'b3_consistent_with_dev': 0.32 <= covered['b3_20'] / N <= 0.72,
        'api_comparable': covered['api_20'] >= covered['b3_20'] - 3,
        'complementary': ('undecidable' if len(miss) < 5 else added / len(miss) >= 0.20),
        'unreachable_share': round(sum(not r['union_all'] for r in rows) / N, 3)}
    summary = {'pairs': N, 'covered': covered, 'wilson95': {k: wilson(covered[k], N) for k in keys},
               'on_b3_20_misses': {'pairs': len(miss), 'api_20': added, 'api_40': sum(r['api_40'] for r in miss), 'api_all': sum(r['api_all'] for r in miss)},
               'pool_size': {'b3': pool_stat('b3_pool'), 'api': pool_stat('api_pool')}, 'generic_ids': pool_stat('generic_ids'),
               'unreachable_by_both_pools': sum(not r['union_all'] for r in rows), 'reading': reading}
    target.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
