"""After labels_103.json is hashed (plan.md): test-retest agreement with the earlier 42 Claude labels, and B3/API coverage
on the 103 pairs by label, type and parallel-directory stratum. WSL; no model calls. Output: analysis.json; prints it.
"""
from collections import Counter
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'p1pp_coverage_20261029'))
import measure_coverage as M  # noqa: E402

S, P = M.S, M.P
CATS = ('yes', 'partial', 'no')


def kappa(a, b, cats):
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def coverage(f):
    pair = {'seed': f['seed'], 'target': f['target'], 't_targets': f['xarch_targets']}
    s_files = S.seed_files(pair['seed'])
    s_rels = {S.rel(x) for x in s_files if S.rel(x)}
    uni = S.universe(P.tree_files(pair['seed']), s_files)
    texts = P.read_files(pair['seed'], uni)
    b3, api = M.b3_full(pair, uni, s_rels, texts), M.api_full(uni, texts, M.generic_ids(pair))
    tg = {tuple(x) for x in pair['t_targets']}
    cov = lambda c: any(x in tg for x in c)
    dirs = {S.rel_dir(r) for r in s_rels}
    return {'b3_20': cov(b3[:20]), 'api_20': cov(api[:20]), 'union_20_20': cov(b3[:20] + api[:20]), 'union_all': cov(b3 + api),
            'same_dir_target': any(S.rel(p) is not None and S.rel_dir(S.rel(p)) in dirs for p, _ in pair['t_targets'])}


def main():
    target = HERE / 'analysis.json'
    if target.exists():
        raise SystemExit('preserve')
    labels = {r['id']: r for r in json.loads((HERE / 'labels_103.json').read_text(encoding='utf-8'))['labels']}
    rows = [f for f in json.loads((C / 'sibling_dataset_20261029' / 'sibling_dataset.json').read_text())['pairs']
            if f['dup_of'] is None and not f['self_duplicate']]
    old = {(r['seed'], r['target']): r for r in json.loads((C / 'sibling_dataset_20261029' / 'claude_labels.json').read_text())['labels']}
    a, b, roles = [], [], []
    for f in rows:
        o = old.get((f['seed'], f['target']))
        if o:
            a.append(o['sibling'])
            b.append(labels[f['id']]['sibling'])
            roles.append((o['seed_role'], labels[f['id']]['seed_role']))
    agree = {'matched_pairs': len(a), 'sibling_agreement': round(sum(x == y for x, y in zip(a, b)) / len(a), 3) if a else None,
             'sibling_kappa_3class': kappa(a, b, CATS),
             'yes_vs_not_kappa': kappa(['yes' if x == 'yes' else 'not' for x in a], ['yes' if x == 'yes' else 'not' for x in b], ('yes', 'not')),
             'transitions': dict(Counter('%s->%s' % (x, y) for x, y in zip(a, b))),
             'seed_role_agreement': round(sum(x == y for x, y in roles) / len(roles), 3) if roles else None}
    per = []
    for f in rows:
        lab = labels[f['id']]
        per.append({'id': f['id'], 'type': f['type'], 'sibling': lab['sibling'], 'seed_role': lab['seed_role'], **coverage(f)})
        print(f['id'], flush=True)
    keys = ('b3_20', 'api_20', 'union_20_20', 'union_all')
    tally = lambda rs: {'pairs': len(rs), **{k: sum(r[k] for r in rs) for k in keys}}
    yes = [r for r in per if r['sibling'] == 'yes']
    out = {'agreement_with_earlier_42': agree,
           'label_counts': dict(Counter(r['sibling'] for r in per)),
           'label_by_type': {t: dict(Counter(r['sibling'] for r in per if r['type'] == t)) for t in sorted({r['type'] for r in per})},
           'seed_role_by_type': {t: dict(Counter(r['seed_role'] for r in per if r['type'] == t)) for t in sorted({r['type'] for r in per})},
           'coverage': {'all': tally(per), 'yes': tally(yes), 'partial': tally([r for r in per if r['sibling'] == 'partial']),
                        'no': tally([r for r in per if r['sibling'] == 'no']),
                        'yes_by_type': {t: tally([r for r in yes if r['type'] == t]) for t in sorted({r['type'] for r in yes})},
                        'yes_same_dir': tally([r for r in yes if r['same_dir_target']]),
                        'yes_not_same_dir': tally([r for r in yes if not r['same_dir_target']]),
                        'all_same_dir': tally([r for r in per if r['same_dir_target']]),
                        'all_not_same_dir': tally([r for r in per if not r['same_dir_target']])}}
    target.write_text(json.dumps({**out, 'rows': per}, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
