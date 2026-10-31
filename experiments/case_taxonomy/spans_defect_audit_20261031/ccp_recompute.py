"""Audit step 3 (criteria.md): recompute contract-change candidate coverage (v1 of ccp_feasibility, v2 of ccp_candgen_v2)
with the corrected recogniser for both targets and candidates, on the same pairs (fresh 238; main = untouched 208).
WSL; counts only. Output: ccp_recompute.json.
"""
from pathlib import Path
import json
import statistics
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(C / 'ccp_candgen_v2_20261030'))
import wide_spans as W  # noqa: E402
import count_v2 as CV  # noqa: E402

CC = CV.CC
BD, X = CC.BD, CC.X
BD.named_spans = W.named_spans
CC.named_spans = W.named_spans


def v1_ids(c):
    ids_all = CC.idents([l for ls in CC.diff_lines(c, True).values() for l in ls])
    df = CC.doc_freq(c, ids_all) if ids_all else {}
    return {i for i in ids_all if 0 < df.get(i, 0) <= CC.MAX_DF}


def cov(cands, tg):
    rank = [i for i, x in enumerate(cands) if tuple(x[:2]) in tg]
    return {'all': bool(rank), 'top20': bool(rank) and rank[0] < 20, 'top50': bool(rank) and rank[0] < 50, 'pool': len(cands)}


def summary(rs, v):
    pools = sorted(r[v]['pool'] for r in rs)
    share = lambda k: round(sum(r[v][k] for r in rs) / len(rs), 3)
    return {'pairs': len(rs), 'cov_all': share('all'), 'cov_50': share('top50'), 'cov_20': share('top20'),
            'pool_median': statistics.median(pools)}


def main():
    target = HERE / 'ccp_recompute.json'
    if target.exists():
        raise SystemExit('preserve')
    rows_v2 = {(r['seed'], r['target']): r for r in json.loads((C / 'ccp_candgen_v2_20261030' / 'v2_pool.json').read_text())['rows']}
    pool = [p for p in json.loads((C / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs'] if not p['overlap_commit']]
    rows = []
    for n, p in enumerate(pool, 1):
        c, t, ca = p['seed'], p['target'], set(p['c_arches'])
        tg = {tuple(y) for y in BD.body_targets_strict(t, c) if X.arch_of(y[0]) and X.arch_of(y[0]) not in ca}
        v1 = cov(CC.candidates(c, v1_ids(c), ca), tg)
        v2 = cov(CV.candidates_v2(c, CV.keys_of(c), ca), tg)
        old = rows_v2.get((c, t), {})
        rows.append({'seed': c, 'target': t, 'audited': old.get('audited'), 'targets_wide': sorted(tg), 'v1': v1, 'v2': v2,
                     'v1_old': {'all': p['cov_all'], 'top20': p['cov_20'], 'top50': p['cov_50'], 'pool': p['pool']},
                     'v2_old': {'all': old.get('cov_all_v2'), 'top20': old.get('cov_20_v2'), 'top50': old.get('cov_50_v2'), 'pool': old.get('pool_v2')}})
        if n % 25 == 0:
            print('progress', n, len(pool), flush=True)
    main_rows = [r for r in rows if not r['audited']]
    out = {'fresh': {v: summary(rows, v) for v in ('v1', 'v1_old', 'v2', 'v2_old')},
           'main_untouched': {v: summary(main_rows, v) for v in ('v1', 'v1_old', 'v2', 'v2_old')}}
    target.write_text(json.dumps({'summary': out, 'rows': rows}, indent=1) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
