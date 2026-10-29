"""Target-correction sensitivity (plan.md section 2). WSL; no model calls; registered results are not changed.
P1': saved top-20 candidates vs strict targets. Coverage: measure_coverage functions rerun with strict targets.
Empty strict targets are reported both kept in the denominator and dropped. Output: sensitivity.json; prints it.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'sibling_dataset_20261029'))
sys.path.insert(0, str(C / 'p1pp_coverage_20261029'))
import build_dataset as BD  # noqa: E402
import measure_coverage as M  # noqa: E402

S, P, X = M.S, M.P, BD.X


def strict(seed, target):
    sa = X.arches(X.meta_of(seed, {})['files'])
    return {y for y in BD.body_targets_strict(target, seed) if X.arch_of(y[0]) and X.arch_of(y[0]) not in sa}


def coverage(pair, tg):
    s_files = S.seed_files(pair['seed'])
    s_rels = {S.rel(f) for f in s_files if S.rel(f)}
    uni = S.universe(P.tree_files(pair['seed']), s_files)
    texts = P.read_files(pair['seed'], uni)
    b3, api = M.b3_full(pair, uni, s_rels, texts), M.api_full(uni, texts, M.generic_ids(pair))
    cov = lambda c: any(x in tg for x in c)
    return {'b3_20': cov(b3[:20]), 'api_20': cov(api[:20]), 'union_20_20': cov(b3[:20] + api[:20]), 'union_all': cov(b3 + api)}


def tally(rows, keys):
    keep = {k: [len(rows), sum(r[k] for r in rows)] for k in keys}
    nonempty = [r for r in rows if not r['empty']]
    drop = {k: [len(nonempty), sum(r[k] for r in nonempty)] for k in keys}
    return {'kept_in_denominator': keep, 'empty_dropped': drop}


def main():
    target = HERE / 'sensitivity.json'
    if target.exists():
        raise SystemExit('preserve')
    dev = json.loads((C / 'p1prime_20261029' / 'p1prime_sample.json').read_text())['sample']
    res = json.loads((C / 'p1prime_20261029' / 'run' / 'p1prime_results.json').read_text())['rows']
    hold = json.loads((C / 'p1pp_design_20261029' / 'holdout_pool.json').read_text())['usable']
    p1, dcov = [], []
    for n, (p, r) in enumerate(zip(dev, res), 1):
        tg = strict(p['seed'], p['target'])
        changed = tg != {tuple(x) for x in p['t_targets']}
        hit = {k: any(tuple(c) in tg for c in r[k]['candidates']) for k in ('m5', 'b2', 'b3')}
        p1.append({'n': n, 'empty': not tg, 'changed': changed, **hit})
        dcov.append({'n': n, 'empty': not tg, 'changed': changed, **coverage({'seed': p['seed'], 'target': p['target'], 't_targets': sorted(tg)}, tg)})
        print('dev', n, flush=True)
    hcov = []
    for n, p in enumerate(hold, 1):
        tg = strict(p['seed'], p['target'])
        hcov.append({'n': n, 'empty': not tg, 'changed': tg != {tuple(x) for x in p['xarch_targets']},
                     **coverage({'seed': p['seed'], 'target': p['target'], 't_targets': sorted(tg)}, tg)})
        print('hold', n, flush=True)
    nonempty = [r for r in p1 if not r['empty']]
    tests = {lab: {'m5_vs_b2': P.mcnemar([r['m5'] for r in rs], [r['b2'] for r in rs]),
                   'm5_vs_b3': P.mcnemar([r['m5'] for r in rs], [r['b3'] for r in rs])}
             for lab, rs in (('kept_in_denominator', p1), ('empty_dropped', nonempty))}
    ck = ['b3_20', 'api_20', 'union_20_20', 'union_all']
    out = {'p1prime': {'changed': sum(r['changed'] for r in p1), 'empty': sum(r['empty'] for r in p1),
                       'recall': tally(p1, ['m5', 'b2', 'b3']), 'mcnemar': tests,
                       'registered': {'m5': 15, 'b2': 9, 'b3': 26, 'pairs': 50}},
           'dev_coverage': {'changed': sum(r['changed'] for r in dcov), 'empty': sum(r['empty'] for r in dcov), 'covered': tally(dcov, ck),
                            'registered': {'b3_20': 26, 'api_20': 25, 'union_20_20': 33, 'union_all': 39, 'pairs': 50}},
           'holdout_coverage': {'changed': sum(r['changed'] for r in hcov), 'empty': sum(r['empty'] for r in hcov), 'covered': tally(hcov, ck),
                                'registered': {'b3_20': 5, 'api_20': 5, 'union_20_20': 7, 'union_all': 9, 'pairs': 22}}}
    target.write_text(json.dumps({**out, 'rows': {'p1prime': p1, 'dev_coverage': dcov, 'holdout_coverage': hcov}}, indent=1) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
