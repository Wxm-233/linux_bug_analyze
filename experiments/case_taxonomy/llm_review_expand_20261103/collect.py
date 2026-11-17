"""Candidates (criteria.md section 1): flags of the frozen version-2 rules on v6.1 and the new snapshots, minus every
key reviewed or labelled before (the 41 + 18 items and the exclusions of llm_review_facts_20261103/candidates.py),
earliest snapshot kept; a seeded sample of 60 if more. No git, no model. Output: candidates.json."""
from pathlib import Path
import importlib.util
import json
import random

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location('cand', ROOT / 'llm_review_facts_20261103' / 'candidates.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
SNAPS = ['v6.1', 'v6.2', 'v6.3', 'v6.4', 'v6.5', 'v6.7', 'v6.8', 'v6.9', 'v6.10', 'v6.11', 'v6.13', 'v6.14', 'v6.15',
         'v6.16', 'v6.17', 'v6.18', 'v6.19', 'v7.0', 'v7.1', 'v7.2']
LIMIT, SEED = 60, 20261103


def load(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))


def excluded():
    seen = {tuple(it['key']) for it in load('llm_review_rule_flags_20261103/items.json')}
    seen |= {tuple(c['key']) for c in load('llm_review_facts_20261103/candidates.json')}
    flags = load('ctx_rules_riscv_20261103/flags_run2.json')['flags']
    for r in load('ctx_rules_riscv_20261103/manual_review.json')['rows']:
        f = flags[r['i']]
        seen.add(('CTX', f['function'], f['sink'], f['call']))
    for r in load('mech_rules_riscv_20261103/review_sample.json'):
        seen.add((r['rule'], r['name']))
    for f in load('rules_v2_forward_end_20261103/flags_end.json')['flags']:
        seen.add(C.key(f))
    return seen


def main():
    if (HERE / 'candidates.json').exists():
        raise SystemExit('preserve')
    seen, keys, pool, per_snap = excluded(), set(), [], {}
    for snap in SNAPS:
        p = ('rules_v2_unified_20261103/flags_eval_v6.1.json' if snap == 'v6.1'
             else f'llm_review_expand_20261103/flags/flags_{snap}.json')
        flags = load(p)['flags']
        n = 0
        for f in flags:
            k = C.key(f)
            if k in seen or k in keys:
                continue
            keys.add(k)
            n += 1
            pool.append({'snapshot': snap, 'source_file': p, **{x: f.get(x) for x in
                         ('rule', 'path', 'name', 'start', 'end', 'reason', 'chain', 'refs', 'kind', 'source', 'issue')},
                         'key': list(k)})
        per_snap[snap] = {'flags': len(flags), 'new_keys': n}
    picked = pool if len(pool) <= LIMIT else sorted(random.Random(SEED).sample(pool, LIMIT),
                                                      key=lambda c: (SNAPS.index(c['snapshot']), c['rule'], c['name']))
    for k, c in enumerate(picked):
        c['cand'] = k
    out = {'pool': len(pool), 'sampled': len(pool) > LIMIT, 'per_snapshot': per_snap, 'rows': picked}
    (HERE / 'candidates.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(per_snap), 'pool', len(pool), 'picked', len(picked))
    for c in picked:
        print(c['cand'], c['snapshot'], c['rule'], c['path'].replace('arch/riscv/', ''), c['name'], '|', (c['reason'] or '')[:100])


if __name__ == '__main__':
    main()
