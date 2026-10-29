"""P1'' held-out pool count (criteria.md). WSL; no model calls; prints counts only.
Reuses xarch_source_20261029/count_xarch.py (funnel, targets) and xarch_source_v419_20261029/count_v419.py (all-time contact scan),
with range v4.0..df2908090cda, source B restricted to seeds that carry Fixes: themselves, and P1' dev-set isolation.
Output: holdout_pool.json.
"""
from pathlib import Path
import itertools
import json
import random
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'xarch_source_v419_20261029'))
import count_v419 as V  # noqa: E402

X = V.X
X.RANGE = 'v4.0..df2908090cda'
V.HERE = HERE
V.PROGRAM_LISTS = V.PROGRAM_LISTS | {C / 'xarch_source_v419_20261029' / 'xarch_pairs_v419.json'}
PER_X = 3
SPLIT = 'v4.19'


def main():
    target = HERE / 'holdout_pool.json'
    if target.exists():
        raise SystemExit('preserve')
    fixers = X.log_fixes()
    res = X.resolve({t for r in fixers.values() for t in r['fixes']})
    groups = {}
    for h, r in fixers.items():
        for x in sorted({res[t] for t in r['fixes'] if t in res}):
            groups.setdefault(x, []).append(h)
    cache = dict(fixers)
    raw = {'A': [], 'B': []}
    b_dropped = 0
    for x, hs in groups.items():
        hs = sorted(set(hs), key=lambda h: (fixers[h]['time'], h))
        if not x.startswith(X.ROOT_COMMIT):
            raw['A'] += [(s, t, x) for s, t in itertools.combinations(hs, 2)]
        if x in fixers:
            raw['B'] += [(x, t, x) for t in hs]
        else:
            b_dropped += len(hs)
    funnel = {k: dict.fromkeys(['pairs', 'arch', 'disjoint_arch', 'valid_target', 'not_all_seed'], 0) for k in raw}
    final = []
    for src, pairs in raw.items():
        for s, t, x in pairs:
            funnel[src]['pairs'] += 1
            sm, tm = X.meta_of(s, cache), X.meta_of(t, cache)
            sa, ta = X.arches(sm['files']), X.arches(tm['files'])
            if not sa or not ta:
                continue
            funnel[src]['arch'] += 1
            if not ta - sa:
                continue
            funnel[src]['disjoint_arch'] += 1
            xt = sorted(y for y in X.body_targets(t, s) if X.arch_of(y[0]) and X.arch_of(y[0]) not in sa)
            if not xt:
                continue
            funnel[src]['valid_target'] += 1
            if set(xt) <= X.changed_functions(s):
                continue
            funnel[src]['not_all_seed'] += 1
            final.append({'source': src, 'seed': s, 'target': t, 'x': x, 'time_s': sm['time'], 'time_t': tm['time'],
                          'different_author': sm['author'] != tm['author'], 'xarch_targets': xt})
    p0b = json.loads((C / 'p0b_20261029' / 'pairs_b.json').read_text())
    p0b_dev = {h for p in p0b['dev'] for h in (p['seed'], p['target'])}
    held = sorted(p0b['held_out'], key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(held)
    p1_seen = {h for p in held[:124] for h in (p['seed'], p['target'])}
    listed = set()
    for name in ('frozen_sample.txt', 'contacted_candidates.txt', 'family_linked_candidates.txt'):
        listed |= set((X.s3.S1 / name).read_text().split())
    dev = json.loads((C / 'p1prime_20261029' / 'p1prime_sample.json').read_text())['sample']
    dev_commits = {h for p in dev for h in (p['seed'], p['target'])}
    dev_x = {p['x'] for p in dev}
    cand = {h for f in final for h in (f['seed'], f['target'])}
    alltime, scan_info = V.scan(cand, 0)
    touched = (p0b_dev | p1_seen | listed | alltime) & cand
    steps = {'final_pairs': len(final)}
    rows = [f for f in final if f['seed'] not in touched and f['target'] not in touched]
    steps['after_contact'] = len(rows)
    rows = [f for f in rows if f['seed'] not in dev_commits and f['target'] not in dev_commits and f['x'] not in dev_x]
    steps['after_dev_isolation'] = len(rows)
    by_t = {}
    for f in rows:
        by_t.setdefault(f['target'], []).append(f)
    chosen = {}
    for t, fs in by_t.items():
        b = [f for f in fs if f['source'] == 'B']
        pool = b or [f for f in fs if f['time_s'] < f['time_t']] or fs
        chosen[t] = sorted(pool, key=lambda f: (-f['time_s'], f['seed']))[0]
    steps['distinct_targets'] = len(chosen)
    per_x, usable = {}, []
    for t in sorted(chosen, key=lambda t: (chosen[t]['time_t'], t)):
        f = chosen[t]
        if per_x.get(f['x'], 0) >= PER_X:
            continue
        per_x[f['x']] = per_x.get(f['x'], 0) + 1
        usable.append(f)
    steps['after_x_cap'] = len(usable)
    split_time = int(subprocess.run(['git', '-C', X.REPO, 'log', '-1', '--format=%ct', SPLIT], capture_output=True, text=True).stdout.strip())
    describe = {'source_A': sum(f['source'] == 'A' for f in usable), 'source_B': sum(f['source'] == 'B' for f in usable),
                't_before_v4_19': sum(f['time_t'] < split_time for f in usable), 't_after_v4_19': sum(f['time_t'] >= split_time for f in usable),
                'different_author': sum(f['different_author'] for f in usable), 'distinct_x': len({f['x'] for f in usable})}
    n = len(usable)
    decision = 'register_p1pp' if n >= 50 else 'register_limited_power' if n >= 30 else 'holdout_insufficient'
    out = {'range': X.RANGE, 'fixers_in_range': len(fixers), 'source_B_dropped_seed_not_fix': b_dropped, 'funnel': funnel,
           'steps': steps, 'describe': describe, 'contacts': {'touched_hits': len(touched), 'scan': scan_info},
           'decision': decision, 'usable': usable}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'usable'}))


if __name__ == '__main__':
    main()
