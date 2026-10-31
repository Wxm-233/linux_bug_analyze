"""Candidate generation v2 (criteria.md). WSL; no model calls; prints counts only.
Adds to v1 (count_ccp.py): function-name match, names of the common functions C edits, member-access form for
high-df names, and one-level callees of those functions (name match only). Records which source hits each target.
Usage: python3 count_v2.py smoke   (audited 30 pairs, prints, writes nothing)
       python3 count_v2.py         (fresh pairs and RISC-V pairs -> v2_pool.json, stats.json)
"""
from pathlib import Path
import json
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
sys.path.insert(0, str(C_DIR / 'ccp_feasibility_20261030'))
import count_ccp as CC  # noqa: E402

X, P, WORD, MAX_DF = CC.X, CC.P, CC.WORD, CC.MAX_DF
C_WORDS = CC.C_WORDS
HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
CALL = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
MEMBER = re.compile(r'(?:->|\.)([A-Za-z_]\w*)\b')
SOURCES = ('v1', 'name_v1', 'enc_body', 'enc_name', 'mem', 'callee_name')
ABLATION = {'v1': {'v1'}, '+name': {'v1', 'name_v1'}, '+enclosing': {'v1', 'enc_body'},
            '+member': {'v1', 'mem'}, '+callee': {'v1', 'callee_name'}, 'v2': set(SOURCES)}


def usable(names):
    return {n for n in names if len(n) >= 4 and n not in C_WORDS}


def changed_ranges(commit):
    """{common path: [(start, end)]}: new-side line ranges of C's hunks in non-arch .c/.h files."""
    out, path = {}, None
    for line in P['git']('show', '--format=', '-U0', '--no-renames', commit, '--', '*.c', '*.h').splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') and not line[6:].startswith('arch/') else None
            continue
        m = HUNK.match(line) if path else None
        if m:
            s, n = int(m.group(1)), int(m.group(2) or 1)
            out.setdefault(path, []).append((s, s + max(n, 1) - 1))
    return out


def header_start(lines, s):
    """First line of the declaration before the body opening at line s (1-based); spans start at '{'."""
    h = s
    while h > 1 and s - h < 6:
        prev = lines[h - 2].strip()
        if not prev or prev.endswith((';', '}', '*/')) or prev.startswith('#'):
            break
        h -= 1
    return h


def enclosing(commit):
    """Names of common functions whose header or body C edits, and the names those bodies call (snapshot C)."""
    rng = changed_ranges(commit)
    texts = P['blobs'](['%s:%s' % (commit, f) for f in rng])
    names, calls = set(), set()
    for f, rs in rng.items():
        text = texts.get('%s:%s' % (commit, f))
        if not text:
            continue
        lines = text.splitlines()
        for s, e, name in CC.named_spans(text):
            if any(a <= e and b >= header_start(lines, s) for a, b in rs):
                names.add(name)
                calls |= set(CALL.findall('\n'.join(lines[s - 1:e])))
    return usable(names), usable(calls) - names


def member_freq(commit, names):
    """Files where each name appears in member-access form (->name or .name)."""
    df, names = {}, sorted(names)
    for k in range(0, len(names), 150):
        chunk = names[k:k + 150]
        out = P['git']('grep', '-o', '-E', r'(->|\.)(%s)\b' % '|'.join(map(re.escape, chunk)), commit, '--', '*.c', '*.h')
        for line in out.splitlines():
            parts = line.split(':', 2)
            if len(parts) == 3:
                df.setdefault(parts[2].lstrip('->.'), set()).add(parts[1])
    return {k: len(v) for k, v in df.items()}


def keys_of(commit):
    """Identifier sets per source; v1 ids are exactly count_ccp's."""
    lines = [l for ls in CC.diff_lines(commit, True).values() for l in ls]
    ids_all = CC.idents(lines)
    enc, calls = enclosing(commit)
    mem_all = usable(m for l in lines for m in MEMBER.findall(l))
    df = CC.doc_freq(commit, ids_all | enc | calls | mem_all) if ids_all | enc | calls | mem_all else {}
    ok = lambda i: 0 < df.get(i, 0) <= MAX_DF
    v1 = {i for i in ids_all if ok(i)}
    enc_ids = {i for i in enc if ok(i)} - v1
    callee = {i for i in calls if ok(i)} - v1 - enc_ids
    high = {m for m in mem_all if df.get(m, 0) > MAX_DF}
    mdf = member_freq(commit, high) if high else {}
    mem = {m for m in high if 0 < mdf.get(m, 0) <= MAX_DF}
    return {'v1': v1, 'enc': enc_ids, 'callee': callee, 'mem': mem}


def candidates_v2(commit, keys, c_arches):
    """[(file, name, sources)] for functions in arch dirs C did not touch, ranked by distinct hit keys."""
    k = keys
    words = k['v1'] | k['enc'] | k['callee'] | k['mem']
    if not words:
        return []
    files, ws = set(), sorted(words)
    for i in range(0, len(ws), 150):
        chunk = ws[i:i + 150]
        out = P['git']('grep', '-l', '-w', '-E', '(%s)' % '|'.join(map(re.escape, chunk)), commit, '--', 'arch/*.c', 'arch/*.h')
        files |= {l.split(':', 1)[1] for l in out.splitlines() if ':' in l}
    files = sorted(f for f in files if X.arch_of(f) and X.arch_of(f) not in c_arches)
    texts = P['blobs'](['%s:%s' % (commit, f) for f in files])
    scored = []
    for f in files:
        text = texts.get('%s:%s' % (commit, f))
        if not text:
            continue
        lines = text.splitlines()
        for s, e, name in CC.named_spans(text):
            body = '\n'.join(lines[s - 1:e])
            bw = set(WORD.findall(body))
            hits, src = set(), set()
            if bw & k['v1']:
                hits |= bw & k['v1']
                src.add('v1')
            if bw & k['enc']:
                hits |= bw & k['enc']
                src.add('enc_body')
            mh = set(MEMBER.findall(body)) & k['mem']
            if mh:
                hits |= {'.' + m for m in mh}
                src.add('mem')
            for key, tag in (('v1', 'name_v1'), ('enc', 'enc_name'), ('callee', 'callee_name')):
                if name in k[key]:
                    hits.add('name:' + name)
                    src.add(tag)
            if hits:
                scored.append((-len(hits), f, s, name, sorted(src)))
    scored.sort()
    return [(f, n, src) for _, f, _, n, src in scored]


def score(p):
    c, tg = p['seed'], {tuple(x) for x in p['targets']}
    keys = keys_of(c)
    cands = candidates_v2(c, keys, set(p['c_arches']))
    hit = set()
    for f, n, src in cands:
        if (f, n) in tg:
            hit |= set(src)
    rank = [i for i, (f, n, _) in enumerate(cands) if (f, n) in tg]
    return {'seed': c, 'target': p['target'], 'target_arches': sorted({X.arch_of(t[0]) for t in p['targets']}),
            'keys': {k: len(v) for k, v in keys.items()}, 'pool_v1': p['pool'], 'cov_all_v1': p['cov_all'],
            'cov_20_v1': p['cov_20'], 'cov_50_v1': p['cov_50'], 'pool_v2': len(cands), 'best_rank_v2': rank[0] + 1 if rank else None,
            'cov_20_v2': bool(rank) and rank[0] < 20, 'cov_50_v2': bool(rank) and rank[0] < 50, 'cov_all_v2': bool(rank),
            'hit_sources': sorted(hit)}


def summary(rs):
    if not rs:
        return None
    share = lambda key: round(sum(1 for r in rs if r[key]) / len(rs), 3)
    pools = lambda key: sorted(r[key] for r in rs)
    out = {'pairs': len(rs)}
    for v in ('v1', 'v2'):
        ps = pools('pool_' + v)
        out[v] = {'cov_20': share('cov_20_' + v), 'cov_50': share('cov_50_' + v), 'cov_all': share('cov_all_' + v),
                  'pool_median': statistics.median(ps), 'pool_q3': ps[int(len(ps) * 0.75)]}
    out['ablation_cov_all'] = {a: round(sum(1 for r in rs if set(r['hit_sources']) & s) / len(rs), 3) for a, s in ABLATION.items()}
    out['v1_recomputed_matches_stored'] = sum(1 for r in rs if ('v1' in r['hit_sources']) == r['cov_all_v1'])
    return out


def main():
    pool = json.loads((C_DIR / 'ccp_feasibility_20261030' / 'ccp_pool.json').read_text())['pairs']
    audited = {(l['seed'], l['target']): l for l in json.loads((C_DIR / 'ccp_audit_20261030' / 'audit_30.json').read_text(encoding='utf-8'))['labels']}
    if sys.argv[1:] == ['smoke']:
        for p in pool:
            l = audited.get((p['seed'], p['target']))
            if l and l['follow_up'] == 'yes':
                r = score(p)
                print(l['n'], 'v1', r['cov_all_v1'], 'v2', r['cov_all_v2'], r['best_rank_v2'], r['pool_v1'], r['pool_v2'], r['hit_sources'], flush=True)
        return
    target = HERE / 'v2_pool.json'
    if target.exists():
        raise SystemExit('preserve')
    riscv = lambda p: any(X.arch_of(t[0]) == 'riscv' for t in p['targets'])
    chosen = [p for p in pool if not p['overlap_commit'] or riscv(p)]
    rows = []
    for n, p in enumerate(chosen, 1):
        r = score(p)
        key = (p['seed'], p['target'])
        r.update({'fresh': not p['overlap_commit'], 'audited': key in audited,
                  'audit_label': audited[key]['follow_up'] if key in audited else None})
        rows.append(r)
        if n % 25 == 0:
            print('progress', n, len(chosen), flush=True)
    main_rows = [r for r in rows if r['fresh'] and not r['audited']]
    s = summary(main_rows)
    ok = s['v2']['cov_all'] >= 0.5
    stats = {'main_untouched': s, 'reference_audited_all': summary([r for r in rows if r['audited']]),
             'reference_audited_yes': summary([r for r in rows if r['audit_label'] == 'yes']),
             'riscv_existing_function_pairs': [{k: r[k] for k in ('seed', 'target', 'fresh', 'audited', 'cov_all_v1', 'cov_all_v2', 'pool_v2', 'best_rank_v2')}
                                               for r in rows if 'riscv' in r['target_arches']],
             'decision': ('usable_register_judgement' if ok and s['v2']['pool_median'] <= 200 else
                          'coverage_ok_pool_too_large' if ok else 'coverage_insufficient_design_same_position'),
             'kimi_calls': 0}
    target.write_text(json.dumps({'rows': rows}, indent=1) + '\n')
    (HERE / 'stats.json').write_text(json.dumps(stats, indent=1) + '\n')
    print(json.dumps({k: stats[k] for k in ('main_untouched', 'decision')}))


if __name__ == '__main__':
    main()
