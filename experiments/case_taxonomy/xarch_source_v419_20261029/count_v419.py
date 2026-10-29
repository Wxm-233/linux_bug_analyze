"""Cross-arch fix siblings over v4.19..df2908090cda (criteria.md). Reuses xarch_source_20261029/count_xarch.py with the range
replaced, and amendment 1's bulk-list rule for contacts, at two scopes: files changed since 2026-10-27, and all files. WSL; no
model calls. Output: xarch_pairs_v419.json. Prints counts only.
"""
from pathlib import Path
import itertools
import json
import random
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'xarch_source_20261029'))
import count_xarch as X  # noqa: E402

X.RANGE = 'v4.19..df2908090cda'
OLD_RANGE = 'v5.15..df2908090cda'
BULK = 2000
PROGRAM_LISTS = X.SKIP_LISTS | {C / 'xarch_source_20261029' / 'xarch_pairs.json', C / 'xarch_source_20261029' / 'xarch_pairs_amended.json'}


def scan(cand, since):
    """Candidate hashes named in workspace text files (mtime >= since), skipping bulk lists and program-only pool listings."""
    by_prefix = {}
    for h in cand:
        for n in range(10, 17):
            by_prefix.setdefault(h[:n], set()).add(h)
    hit, files, bulk = set(), 0, 0
    skip = PROGRAM_LISTS | {X.INNER / 'candidate_hashes.txt', X.INNER / 'candidate_hashes.txt.audit.jsonl'}
    for r in [X.OUTER] + list(Path('/root').glob('*.md')):
        for p in ([r] if r.is_file() else r.rglob('*')):
            try:
                if (not p.is_file() or p in skip or p.suffix.lower() not in X.s3.TEXT_SUFFIX or HERE in p.parents
                        or p.stat().st_mtime < since or p.stat().st_size > 80_000_000):
                    continue
                data = p.read_bytes()
            except OSError:
                continue
            files += 1
            found, full = set(), 0
            for m in X.s3.TOKEN.finditer(data):
                tok = m.group(1).decode()
                if len(tok) == 40:
                    full += 1
                    if tok in cand:
                        found.add(tok)
                elif len(tok) <= 16 and len(by_prefix.get(tok, ())) == 1:
                    found |= by_prefix[tok]
            if full >= BULK:
                bulk += 1
                continue
            hit |= found
    return hit, {'files_scanned': files, 'bulk_lists_skipped': bulk}


def summarize(rows, key):
    clean = [f for f in rows if f[key]]
    return {'final_pairs': len(rows), 'clean_pairs': len(clean), 'clean_distinct_targets': len({f['target'] for f in clean}),
            'clean_distinct_x': len({f['x'] for f in clean}), 'clean_different_author': sum(f['different_author'] for f in clean),
            'clean_distinct_targets_narrow_x': len({f['target'] for f in clean if f['group_size'] <= X.BROAD})}


def main():
    target = HERE / 'xarch_pairs_v419.json'
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
    for x, hs in groups.items():
        hs = sorted(set(hs), key=lambda h: (fixers[h]['time'], h))
        if not x.startswith(X.ROOT_COMMIT):
            raw['A'] += [(s, t, x, len(hs)) for s, t in itertools.combinations(hs, 2)]
        raw['B'] += [(x, t, x, len(hs)) for t in hs]
    funnel = {k: dict.fromkeys(['pairs', 'arch', 'disjoint_arch', 'valid_target', 'not_all_seed'], 0) for k in raw}
    final = []
    for src, pairs in raw.items():
        for s, t, x, group_size in pairs:
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
            final.append({'source': src, 'seed': s, 'target': t, 'x': x, 'group_size': group_size,
                          'different_author': sm['author'] != tm['author'], 'xarch_targets': xt})
    old = set(subprocess.run(['git', '-C', X.REPO, 'rev-list', OLD_RANGE], capture_output=True, text=True).stdout.split())
    p0b = json.loads((C / 'p0b_20261029' / 'pairs_b.json').read_text())
    p0b_dev = {h for p in p0b['dev'] for h in (p['seed'], p['target'])}
    held = sorted(p0b['held_out'], key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(held)
    p1_seen = {h for p in held[:124] for h in (p['seed'], p['target'])}
    listed = set()
    for name in ('frozen_sample.txt', 'contacted_candidates.txt', 'family_linked_candidates.txt'):
        listed |= set((X.s3.S1 / name).read_text().split())
    cand = {h for f in final for h in (f['seed'], f['target'])}
    base = (p0b_dev | p1_seen | listed) & cand
    recent, recent_info = scan(cand, X.s3.SINCE)
    alltime, all_info = scan(cand, 0)
    for f in final:
        ends = (f['seed'], f['target'])
        f['in_old_range'] = all(h in old for h in ends)
        f['clean_since_1027'] = not any(h in base | recent for h in ends)
        f['clean_all_time'] = not any(h in base | alltime for h in ends)
    summary = {}
    for src in ('A', 'B', 'A_or_B'):
        rows = [f for f in final if src == 'A_or_B' or f['source'] == src]
        summary[src] = {'all_time': summarize(rows, 'clean_all_time'), 'since_1027': summarize(rows, 'clean_since_1027')}
    old_rows = [f for f in final if f['in_old_range']]
    consistency = {'old_range_final_pairs': len(old_rows),
                   'old_range_clean_distinct_targets_since_1027': len({f['target'] for f in old_rows if f['clean_since_1027']}),
                   'expected': 40}
    n = summary['A_or_B']['all_time']['clean_distinct_targets']
    decision = 'register_with_margin' if n >= 50 else 'register_limited_margin' if n >= 40 else 'strict_xarch_insufficient'
    out = {'range': X.RANGE, 'fixers_in_range': len(fixers), 'resolved_x': len(groups), 'funnel': funnel, 'summary': summary,
           'contacts': {'base_hits': len(base), 'since_1027_hits': len(recent & cand), 'all_time_hits': len(alltime & cand),
                        'since_1027_scan': recent_info, 'all_time_scan': all_info},
           'consistency': consistency, 'decision': decision, 'final': final}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'final'}))


if __name__ == '__main__':
    main()
