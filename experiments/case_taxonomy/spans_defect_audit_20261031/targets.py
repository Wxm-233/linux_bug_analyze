"""Audit step 2 (criteria.md): recompute target functions with the original and the corrected recognisers.
- count_pool.body_targets (candidate_bridge spans): P1prime sample (50), held-out pool.
- build_dataset.body_targets_strict (named_spans): sibling dataset (103), contract-change pairs (305) and the
  contract-change funnel step "valid target" (pairs that would enter with the corrected recogniser).
WSL; counts only. Output: targets.json.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(C / 'ccp_feasibility_20261030'))
import wide_spans as W  # noqa: E402
import count_ccp as CC  # noqa: E402

BD, X = CC.BD, CC.X
CP = sys.modules[X.body_targets.__module__]
ORIG = {'bridge': CP.function_spans, 'strict': BD.named_spans}


def both(kind, t, s):
    """(original, corrected) target sets."""
    if kind == 'bridge':
        CP.function_spans = ORIG['bridge']
        a = CP.body_targets(t, s)
        CP.function_spans = W.function_spans
        b = CP.body_targets(t, s)
        CP.function_spans = ORIG['bridge']
    else:
        BD.named_spans = ORIG['strict']
        a = BD.body_targets_strict(t, s)
        BD.named_spans = W.named_spans
        b = BD.body_targets_strict(t, s)
        BD.named_spans = ORIG['strict']
    return {tuple(x) for x in a}, {tuple(x) for x in b}


def audit(name, kind, rows, stored_key, arch_filter):
    out = {'pairs': len(rows), 'reproduced': 0, 'changed': 0, 'added_targets': 0, 'examples': []}
    for r in rows:
        a, b = both(kind, r['target'], r['seed'])
        keep = lambda xs: {x for x in xs if arch_filter(r, x)}
        a, b = keep(a), keep(b)
        stored = {tuple(x) for x in r[stored_key]}
        out['reproduced'] += a == stored
        if b != a:
            out['changed'] += 1
            out['added_targets'] += len(b - a)
            if len(out['examples']) < 8:
                out['examples'].append({'seed': r['seed'][:12], 'target': r['target'][:12], 'added': sorted(b - a)})
    print(name, {k: v for k, v in out.items() if k != 'examples'}, flush=True)
    return out


def ccp_funnel():
    """count_ccp's pair funnel up to 'valid target', with both recognisers."""
    fixers = X.log_fixes()
    res = X.resolve({t for r in fixers.values() for t in r['fixes']})
    cache = dict(fixers)
    n_orig = n_wide = 0
    new = []
    for t, r in fixers.items():
        if not X.arches(r['files']):
            continue
        for tok in r['fixes']:
            c = res.get(tok)
            if not c or c.startswith(X.ROOT_COMMIT) or c == t:
                continue
            cm = X.meta_of(c, cache)
            if not any(f.endswith(('.c', '.h')) and not f.startswith('arch/') for f in cm['files']):
                continue
            ca = X.arches(cm['files'])
            if not X.arches(r['files']) - ca:
                continue
            a, b = both('strict', t, c)
            a = {y for y in a if X.arch_of(y[0]) and X.arch_of(y[0]) not in ca}
            b = {y for y in b if X.arch_of(y[0]) and X.arch_of(y[0]) not in ca}
            n_orig += bool(a)
            n_wide += bool(b)
            if b and not a:
                new.append({'seed': c[:12], 'target': t[:12], 'targets': sorted(b)})
            break
    print('ccp funnel valid_target', n_orig, n_wide, flush=True)
    return {'valid_target_orig': n_orig, 'valid_target_wide': n_wide, 'new_pairs': new}


def main():
    target = HERE / 'targets.json'
    if target.exists():
        raise SystemExit('preserve')
    p1p = json.loads((C / 'p1prime_20261029' / 'p1prime_sample.json').read_text())['sample']
    hold = json.loads((C / 'p1pp_design_20261029' / 'holdout_pool.json').read_text())['usable']
    sib = json.loads((C / 'sibling_dataset_20261029' / 'sibling_dataset.json').read_text())['pairs']
    ccp = json.loads((C / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs']
    stored_arches = lambda key: (lambda r, x: X.arch_of(x[0]) in {X.arch_of(y[0]) for y in r[key]})
    out = {
        'p1prime_sample': audit('p1prime', 'bridge', p1p, 't_targets', stored_arches('t_targets')),
        'holdout_pool': audit('holdout', 'bridge', hold, 'xarch_targets', stored_arches('xarch_targets')),
        'sibling_dataset': audit('sibling', 'strict', sib, 'xarch_targets', stored_arches('xarch_targets')),
        'ccp_pairs': audit('ccp', 'strict', ccp, 'targets', lambda r, x: X.arch_of(x[0]) and X.arch_of(x[0]) not in set(r['c_arches'])),
        'ccp_funnel': ccp_funnel(),
    }
    target.write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
