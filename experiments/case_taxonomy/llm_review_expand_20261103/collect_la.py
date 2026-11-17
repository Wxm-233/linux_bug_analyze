"""LoongArch candidates (criteria_amendment1.md section 1): flags of rules_la.py on every release snapshot, deduplicated
by candidates.py's key() with the earliest snapshot kept, nothing excluded (LoongArch was never reviewed); a seeded
sample of 60 if more. No git, no model. Output: candidates_la.json."""
from pathlib import Path
import importlib.util
import json
import random

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cand', HERE.parent / 'llm_review_facts_20261103' / 'candidates.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
SNAPS = [f'v6.{k}' for k in range(1, 20)] + ['v7.0', 'v7.1', 'v7.2']
LIMIT, SEED = 60, 20261103


def main():
    if (HERE / 'candidates_la.json').exists():
        raise SystemExit('preserve')
    keys, pool, per_snap = set(), [], {}
    for snap in SNAPS:
        p = f'flags_la/flags_{snap}.json'
        flags = json.loads((HERE / p).read_text(encoding='utf-8'))['flags']
        n = 0
        for f in flags:
            k = C.key(f)
            if k in keys:
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
    (HERE / 'candidates_la.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(per_snap), 'pool', len(pool), 'picked', len(picked))
    for c in picked:
        print(c['cand'], c['snapshot'], c['rule'], c['path'].replace('arch/loongarch/', ''), c['name'], '|',
              (c['reason'] or '')[:100])


if __name__ == '__main__':
    main()
