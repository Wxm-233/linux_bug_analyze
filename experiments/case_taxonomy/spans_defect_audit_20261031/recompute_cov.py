"""Audit step 3 (criteria.md): recompute B3 (structural) and API (interface-user) candidate coverage for the sibling
dataset (103 unique pairs; final yes subset) and the held-out pool (22) with the corrected recogniser, reusing
p1pp_coverage_20261029/measure_coverage.py. Targets: stored, and recomputed with the corrected recogniser.
WSL; no model calls. Output: recompute_cov.json.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(C / 'p1pp_coverage_20261029'))
sys.path.insert(0, str(C / 'ccp_feasibility_20261030'))
import wide_spans as W  # noqa: E402
import measure_coverage as M  # noqa: E402
import count_ccp as CC  # noqa: E402

S, P = M.S, M.P
BD, X = CC.BD, CC.X
CP = sys.modules[X.body_targets.__module__]
P.function_spans = W.function_spans
CP.function_spans = W.function_spans
BD.named_spans = W.named_spans


def cov_row(seed, target, stored, wide):
    pair = {'seed': seed, 'target': target, 't_targets': stored}
    s_files = S.seed_files(seed)
    s_rels = {S.rel(x) for x in s_files if S.rel(x)}
    uni = S.universe(P.tree_files(seed), s_files)
    texts = P.read_files(seed, uni)
    b3, api = M.b3_full(pair, uni, s_rels, texts), M.api_full(uni, texts, M.generic_ids(pair))
    out = {}
    for name, tg in (('stored', {tuple(x) for x in stored}), ('wide', wide)):
        cov = lambda c: any(tuple(x) in tg for x in c)
        out[name] = {'b3_20': cov(b3[:20]), 'api_20': cov(api[:20]), 'union_20_20': cov(b3[:20] + api[:20]), 'union_all': cov(b3 + api)}
    return out


def arch_filter(stored, xs):
    arches = {X.arch_of(f) for f, _ in stored}
    return {tuple(x) for x in xs if X.arch_of(x[0]) in arches}


def main():
    target = HERE / 'recompute_cov.json'
    if target.exists():
        raise SystemExit('preserve')
    sib = [f for f in json.loads((C / 'sibling_dataset_20261029' / 'sibling_dataset.json').read_text())['pairs']
           if f['dup_of'] is None and not f['self_duplicate']]
    final = {r['id']: r['sibling'] for r in json.loads((C / 'sibling_adjudication_20261029' / 'final_labels.json').read_text(encoding='utf-8'))['labels']}
    old_sib = {r['id']: r for r in json.loads((C / 'sibling_labels_20261029' / 'analysis.json').read_text(encoding='utf-8'))['rows']}
    rows = []
    for n, f in enumerate(sib, 1):
        wide = arch_filter(f['xarch_targets'], BD.body_targets_strict(f['target'], f['seed']))
        r = cov_row(f['seed'], f['target'], f['xarch_targets'], wide)
        o = old_sib.get(f['id'], {})
        rows.append({'set': 'sibling', 'id': f['id'], 'final': final.get(f['id']), **r,
                     'old': {k: o.get(k) for k in ('b3_20', 'api_20', 'union_20_20', 'union_all')}})
        print('sibling', n, len(sib), flush=True)
    hold = json.loads((C / 'p1pp_design_20261029' / 'holdout_pool.json').read_text())['usable']
    old_hold = json.loads((C / 'holdout_coverage_20261029' / 'holdout_coverage.json').read_text())['rows']
    for n, f in enumerate(hold, 1):
        wide = arch_filter(f['xarch_targets'], CP.body_targets(f['target'], f['seed']))
        r = cov_row(f['seed'], f['target'], f['xarch_targets'], wide)
        o = old_hold[n - 1]
        rows.append({'set': 'holdout', 'n': n, **r, 'old': {k: o.get(k) for k in ('b3_20', 'api_20', 'union_20_20', 'union_all')}})
        print('holdout', n, len(hold), flush=True)

    def agg(rs):
        keys = ('b3_20', 'api_20', 'union_20_20', 'union_all')
        return {'pairs': len(rs), **{v: {k: sum(1 for r in rs if r[v][k]) for k in keys} for v in ('old', 'stored', 'wide')}}
    summary = {'sibling_all': agg([r for r in rows if r['set'] == 'sibling']),
               'sibling_final_yes': agg([r for r in rows if r['set'] == 'sibling' and r['final'] == 'yes']),
               'holdout': agg([r for r in rows if r['set'] == 'holdout'])}
    target.write_text(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
