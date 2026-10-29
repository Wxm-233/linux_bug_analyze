"""Cross-arch fix siblings from a Fixes:-based pair source (criteria.md incl. the pre-count supplement). WSL; no model calls.
Output: xarch_pairs.json (counts; final pairs keep hashes, source, cross-arch targets, clean flag). Prints counts only.
"""
from pathlib import Path
import itertools
import json
import random
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
INNER = HERE.parents[2]
OUTER = INNER.parent
sys.path.insert(0, str(C / 'p1prime_feasibility_20261029'))
sys.path.insert(0, str(C / 'p1_20261029'))
sys.path.insert(0, str(C / 'scoped_sampling_20261028'))
from count_pool import body_targets, arch_of  # noqa: E402
from select_p1 import changed_functions  # noqa: E402
import scoped_select as s3  # noqa: E402

REPO = '/root/repos/linux'
RANGE = 'v5.15..df2908090cda'
ROOT_COMMIT = '1da177e4c3f4'
BROAD = 20
DIE, CLUSTER = '2c4dcd7fd57b20a21b65da04d89c38a7217d79cf', 'e795707703b32fecdd7467afcc33ff1e92416c05'
FIXES = re.compile(r'(?mi)^\s*Fixes:\s*([0-9a-f]{7,40})\b')
SKIP_LISTS = {C / 'p0b_20261029' / 'pairs_b.json', C / 'p1prime_feasibility_20261029' / 'feasibility.json'}


def git(*args, inp=None):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True, input=inp).stdout.decode('utf-8', 'replace')


def log_fixes():
    """{hash: {author, time, files, fixes:[tokens]}} for commits in RANGE whose message has a Fixes: line."""
    out = {}
    raw = git('log', '--no-merges', '--name-only', '--format=%x1e%H%x1f%an%x1f%ct%x1f%B%x1d', RANGE)
    for rec in raw.split('\x1e')[1:]:
        head, _, names = rec.partition('\x1d')
        h, author, ct, body = head.split('\x1f', 3)
        toks = FIXES.findall(body)
        if toks:
            out[h] = {'author': author, 'time': int(ct), 'files': [f for f in names.split('\n') if f.strip()], 'fixes': toks}
    return out


def resolve(tokens):
    toks = sorted(tokens)
    lines = git('cat-file', '--batch-check', inp=''.join(t + '\n' for t in toks).encode()).splitlines()
    return {t: l.split()[0] for t, l in zip(toks, lines) if len(l.split()) == 3 and l.split()[1] == 'commit'}


def meta_of(h, cache):
    if h not in cache:
        r = git('log', '-1', '--name-only', '--format=%an%x1f%ct', h).split('\n')
        author, ct = r[0].split('\x1f')
        cache[h] = {'author': author, 'time': int(ct), 'files': [f for f in r[1:] if f.strip()]}
    return cache[h]


def arches(files):
    return {arch_of(f) for f in files if f.endswith(('.c', '.h'))} - {None}


def recent_hits(cand):
    """s3.recent_contacts with the program-only pool listings and this round's outputs skipped (criteria supplement 2)."""
    by_prefix = {}
    for h in cand:
        for n in range(10, 17):
            by_prefix.setdefault(h[:n], set()).add(h)
    hit, files = set(), 0
    roots = [OUTER] + list(Path('/root').glob('*.md'))
    skip = SKIP_LISTS | {INNER / 'candidate_hashes.txt', INNER / 'candidate_hashes.txt.audit.jsonl'}
    for r in roots:
        for p in ([r] if r.is_file() else r.rglob('*')):
            try:
                if (not p.is_file() or p in skip or p.suffix.lower() not in s3.TEXT_SUFFIX or HERE in p.parents
                        or p.stat().st_mtime < s3.SINCE or p.stat().st_size > 80_000_000):
                    continue
                data = p.read_bytes()
            except OSError:
                continue
            files += 1
            for m in s3.TOKEN.finditer(data):
                tok = m.group(1).decode()
                if len(tok) == 40 and tok in cand:
                    hit.add(tok)
                elif len(tok) <= 16 and len(by_prefix.get(tok, ())) == 1:
                    hit |= by_prefix[tok]
    return hit, files


def main():
    target = HERE / 'xarch_pairs.json'
    if target.exists():
        raise SystemExit('preserve')
    fixers = log_fixes()
    res = resolve({t for r in fixers.values() for t in r['fixes']})
    for r in fixers.values():
        r['x'] = sorted({res[t] for t in r['fixes'] if t in res})
    groups = {}
    for h, r in fixers.items():
        for x in r['x']:
            groups.setdefault(x, []).append(h)
    cache = {h: r for h, r in fixers.items()}
    raw = {'A': [], 'B': []}
    for x, hs in groups.items():
        hs = sorted(set(hs), key=lambda h: (fixers[h]['time'], h))
        if not x.startswith(ROOT_COMMIT):
            for s, t in itertools.combinations(hs, 2):
                raw['A'].append((s, t, x, len(hs)))
        for t in hs:
            raw['B'].append((x, t, x, len(hs)))
    funnel = {k: dict.fromkeys(['pairs', 'arch', 'disjoint_arch', 'valid_target', 'not_all_seed'], 0) for k in raw}
    final = []
    for src, pairs in raw.items():
        for s, t, x, group_size in pairs:
            funnel[src]['pairs'] += 1
            sm, tm = meta_of(s, cache), meta_of(t, cache)
            sa, ta = arches(sm['files']), arches(tm['files'])
            if not sa or not ta:
                continue
            funnel[src]['arch'] += 1
            if not ta - sa:
                continue
            funnel[src]['disjoint_arch'] += 1
            xt = sorted(x_ for x_ in body_targets(t, s) if arch_of(x_[0]) and arch_of(x_[0]) not in sa)
            if not xt:
                continue
            funnel[src]['valid_target'] += 1
            if set(xt) <= changed_functions(s):
                continue
            funnel[src]['not_all_seed'] += 1
            final.append({'source': src, 'seed': s, 'target': t, 'x': x, 'group_size': group_size,
                          'different_author': sm['author'] != tm['author'], 'xarch_targets': xt})
    p0b = json.loads((C / 'p0b_20261029' / 'pairs_b.json').read_text())
    p0b_pool = {h for k in ('dev', 'held_out') for p in p0b[k] for h in (p['seed'], p['target'])}
    p0b_dev = {h for p in p0b['dev'] for h in (p['seed'], p['target'])}
    held = sorted(p0b['held_out'], key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(held)
    p1_seen = {h for p in held[:124] for h in (p['seed'], p['target'])}
    listed = set()
    for name in ('frozen_sample.txt', 'contacted_candidates.txt', 'family_linked_candidates.txt'):
        listed |= set((s3.S1 / name).read_text().split())
    cand = {h for f in final for h in (f['seed'], f['target'])}
    recent, scanned = recent_hits(cand)
    touched = p0b_dev | p1_seen | listed | recent
    for f in final:
        f['clean'] = f['seed'] not in touched and f['target'] not in touched
        f['in_p0b_pool'] = f['seed'] in p0b_pool or f['target'] in p0b_pool
    summary = {}
    for src in ('A', 'B', 'A_or_B'):
        rows = [f for f in final if src == 'A_or_B' or f['source'] == src]
        clean = [f for f in rows if f['clean']]
        summary[src] = {'final_pairs': len(rows), 'clean_pairs': len(clean),
                        'clean_distinct_targets': len({f['target'] for f in clean}),
                        'clean_distinct_x': len({f['x'] for f in clean}),
                        'clean_different_author': sum(f['different_author'] for f in clean),
                        'clean_distinct_targets_narrow_x': len({f['target'] for f in clean if f['group_size'] <= BROAD}),
                        'in_p0b_pool': sum(f['in_p0b_pool'] for f in rows)}
    n = summary['A_or_B']['clean_distinct_targets']
    decision = 'register_strict_xarch_p1prime' if n >= 40 else 'case_set_only' if n >= 10 else 'strict_xarch_retro_infeasible'
    die_cluster = [(f['source'], f['seed'] == DIE and f['target'] == CLUSTER) for f in final if f['target'] == CLUSTER]
    out = {'fixers_in_range': len(fixers), 'resolved_x': len(groups), 'funnel': funnel, 'summary': summary,
           'touched_overlap': {'recent_files_scanned': scanned, 'recent_hits': len(recent & cand), 'touched_total_hits': len(touched & cand)},
           'die_cluster_present': bool(die_cluster), 'decision': decision, 'final': final}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'final'}))


if __name__ == '__main__':
    main()
