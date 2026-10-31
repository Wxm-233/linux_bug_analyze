"""Contract-change propagation feasibility (criteria.md). WSL; no model calls; prints counts only.
Pairs (C, T): T's Fixes: names C, C changes non-arch .c/.h, T edits an existing function body in an arch dir C did not touch.
Measures pool size, symbol linkage (T's arch edits mention C's interface identifiers) and candidate coverage
(functions in untouched arch dirs at snapshot C that mention those identifiers). Output: ccp_pool.json.
"""
from pathlib import Path
import json
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
sys.path.insert(0, str(C_DIR / 'sibling_dataset_20261029'))
import build_dataset as BD  # noqa: E402  (X with range v4.0..df2908090cda, body_targets_strict)
from linux_bug_analyze.candidate_bridge import C_WORDS  # noqa: E402
from linux_bug_analyze.sibling_pairs import named_spans  # noqa: E402

X = BD.X
P = X.body_targets.__globals__  # count_pool module globals (git, blobs)
MAX_DF = 500
WORD = re.compile(r'\b[A-Za-z_]\w*\b')


def diff_lines(commit, common):
    """{path: [changed line text]} for .c/.h files of a commit; common=True keeps non-arch files, False keeps arch files."""
    out, path = {}, None
    for line in P['git']('show', '--format=', '-U0', '--no-renames', commit, '--', '*.c', '*.h').splitlines():
        if line.startswith('+++ ') or line.startswith('--- '):
            p = line[6:] if line[4:6] in ('a/', 'b/') else None
            if p:
                path = p
            continue
        if path and line[:1] in '+-' and (not path.startswith('arch/')) == common:
            out.setdefault(path, []).append(line[1:])
    return out


def idents(lines):
    return {t for l in lines for t in WORD.findall(l) if len(t) >= 4 and t not in C_WORDS}


def doc_freq(commit, ids):
    df = {}
    ids = sorted(ids)
    for k in range(0, len(ids), 150):
        chunk = ids[k:k + 150]
        out = P['git']('grep', '-o', '-w', '-E', '(%s)' % '|'.join(map(re.escape, chunk)), commit, '--', '*.c', '*.h')
        for line in out.splitlines():
            parts = line.split(':', 2)
            if len(parts) == 3:
                df.setdefault(parts[2], set()).add(parts[1])
    return {k: len(v) for k, v in df.items()}


def candidates(commit, ids, c_arches):
    """Functions in arch dirs not touched by C whose body mentions any interface identifier, ranked."""
    if not ids:
        return []
    files = set()
    ids = sorted(ids)
    for k in range(0, len(ids), 150):
        chunk = ids[k:k + 150]
        out = P['git']('grep', '-l', '-w', '-E', '(%s)' % '|'.join(map(re.escape, chunk)), commit, '--', 'arch/*.c', 'arch/*.h')
        files |= {l.split(':', 1)[1] for l in out.splitlines() if ':' in l}
    files = sorted(f for f in files if X.arch_of(f) and X.arch_of(f) not in c_arches)
    texts = P['blobs'](['%s:%s' % (commit, f) for f in files])
    idset, scored = set(ids), []
    for f in files:
        text = texts.get('%s:%s' % (commit, f))
        if not text:
            continue
        lines = text.splitlines()
        for s, e, name in named_spans(text):
            found = set(WORD.findall('\n'.join(lines[s - 1:e]))) & idset
            if found:
                scored.append((-len(found), f, s, name))
    scored.sort()
    return [(f, n) for _, f, _, n in scored]


def main():
    target = HERE / 'ccp_pool.json'
    if target.exists():
        raise SystemExit('preserve')
    fixers = X.log_fixes()
    res = X.resolve({t for r in fixers.values() for t in r['fixes']})
    cache = dict(fixers)
    steps = dict.fromkeys(['t_touch_arch', 'c_common', 'uncovered_arch', 'valid_target'], 0)
    pairs = []
    for t, r in fixers.items():
        if not X.arches(r['files']):
            continue
        steps['t_touch_arch'] += 1
        for tok in r['fixes']:
            c = res.get(tok)
            if not c or c.startswith(X.ROOT_COMMIT) or c == t:
                continue
            cm = X.meta_of(c, cache)
            if not any(f.endswith(('.c', '.h')) and not f.startswith('arch/') for f in cm['files']):
                continue
            steps['c_common'] += 1
            ca = X.arches(cm['files'])
            if not X.arches(r['files']) - ca:
                continue
            steps['uncovered_arch'] += 1
            tg = sorted(y for y in BD.body_targets_strict(t, c) if X.arch_of(y[0]) and X.arch_of(y[0]) not in ca)
            if not tg:
                continue
            steps['valid_target'] += 1
            pairs.append({'seed': c, 'target': t, 'c_arches': sorted(ca), 'targets': tg})
            break
    ds = json.loads((C_DIR / 'sibling_dataset_20261029' / 'sibling_dataset.json').read_text())['pairs']
    seen_pairs = {(f['seed'], f['target']) for f in ds}
    seen_commits = {h for f in ds for h in (f['seed'], f['target'])}
    for n, p in enumerate(pairs, 1):
        c, t = p['seed'], p['target']
        ids_all = idents([l for ls in diff_lines(c, True).values() for l in ls])
        df = doc_freq(c, ids_all) if ids_all else {}
        ids = {i for i in ids_all if 0 < df.get(i, 0) <= MAX_DF}
        t_lines = [l for path, ls in diff_lines(t, False).items() if X.arch_of(path) not in set(p['c_arches']) for l in ls]
        p['linked'] = bool(set(WORD.findall('\n'.join(t_lines))) & ids)
        cands = candidates(c, ids, set(p['c_arches']))
        tg = {tuple(x) for x in p['targets']}
        p.update({'interface_ids': len(ids), 'pool': len(cands), 'cov_20': any(x in tg for x in cands[:20]),
                  'cov_50': any(x in tg for x in cands[:50]), 'cov_all': any(x in tg for x in cands),
                  'overlap_pair': (c, t) in seen_pairs, 'overlap_commit': c in seen_commits or t in seen_commits})
        if n % 50 == 0:
            print('progress', n, len(pairs), flush=True)
    fresh = [p for p in pairs if not p['overlap_commit']]
    pools = sorted(p['pool'] for p in pairs) or [0]
    share = lambda rs, k: round(sum(r[k] for r in rs) / len(rs), 3) if rs else None
    summary = {'range': X.RANGE, 'fixers_in_range': len(fixers), 'steps': steps, 'pairs': len(pairs),
               'overlap_with_sibling_dataset': {'pairs': sum(p['overlap_pair'] for p in pairs), 'commits': sum(p['overlap_commit'] for p in pairs)},
               'fresh_pairs': len(fresh),
               'symbol_linkage': {'all': share(pairs, 'linked'), 'fresh': share(fresh, 'linked')},
               'coverage': {k: {'all': share(pairs, k), 'fresh': share(fresh, k)} for k in ('cov_20', 'cov_50', 'cov_all')},
               'pool_size': {'median': statistics.median(pools), 'q3': pools[int(len(pools) * 0.75)] if pools else 0, 'max': max(pools),
                             'zero': sum(1 for x in pools if x == 0)},
               'no_interface_ids': sum(1 for p in pairs if p['interface_ids'] == 0)}
    fp = sorted(p['pool'] for p in fresh) or [0]
    summary['pool_size_fresh_median'] = statistics.median(fp)
    ok = (len(fresh) >= 50 and (summary['coverage']['cov_all']['fresh'] or 0) >= 0.5 and summary['pool_size_fresh_median'] <= 200)
    summary['decision'] = ('feasible_register_method' if ok else
                           'coverage_insufficient' if len(fresh) >= 50 else 'pool_insufficient')
    target.write_text(json.dumps({'summary': summary, 'pairs': pairs}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
