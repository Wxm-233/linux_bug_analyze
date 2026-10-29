"""P1' instantiation, baselines and scoring (registration_p1prime.md sections 3-6). WSL; no model calls (reads saved final.md).
Refuses to run before the blind audit (audit_first20.json) exists (section 7). Output: p1prime_results.json; prints the summary only.
S's architectures are the arch/<name>/ directories of the .c/.h files S changes, as in the pair source's target definition.
"""
from pathlib import Path
import hashlib
import json
import re
import signal
import sys

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
C = ROUND.parent
CALLS = C.parents[2] / '模型调用测试' / '2026-10-29'
sys.path.insert(0, str(C / 'p1_20261029'))
import score_p1 as P  # noqa: E402  (git, tree_files, read_files, functions, glob_regex, parse_pattern, seed_lines, idents, mcnemar)
from select_p1 import changed_functions  # noqa: E402

TOP, MAX_FILES, FILE_SECONDS = 20, 50_000, 0.5
ARCH = re.compile(r'^arch/([^/]+)/(.*)$')


def rel(path):
    m = ARCH.match(path)
    return m.group(2) if m else None


def seed_files(seed):
    return [f for f in P.git('show', '--name-only', '--format=', seed).stdout.decode('utf-8', 'replace').split() if f.endswith(('.c', '.h'))]


def universe(all_files, s_files):
    s_arches = {ARCH.match(f).group(1) for f in s_files if ARCH.match(f)}
    return [p for p in all_files if ARCH.match(p) and ARCH.match(p).group(1) not in s_arches]


def rel_dir(r):
    return r.rsplit('/', 1)[0] if '/' in r else ''


def tier(path, s_rels):
    r = rel(path)
    if r in s_rels:
        return 0
    return 1 if r is not None and rel_dir(r) in {rel_dir(x) for x in s_rels} else 2


def m5(pair, uni, s_rels, final_text):
    pat = P.parse_pattern(final_text)
    if 'error' in pat:
        return {'status': 'pattern_invalid', 'error': pat['error'], 'candidates': []}
    globs = [P.glob_regex(g) for g in pat['scope']]
    files = [p for p in uni if any(g.match(p) for g in globs)]
    if len(files) > MAX_FILES:
        return {'status': 'search_overrun', 'reason': 'files>%d' % MAX_FILES, 'pattern': pat['raw'], 'candidates': []}
    hits = []
    for path, text in P.read_files(pair['seed'], files).items():
        signal.setitimer(signal.ITIMER_REAL, FILE_SECONDS)
        try:
            for name, line, body in P.functions(text):
                if all(r.search(body) for r in pat['match']) and not any(r.search(body) for r in pat['fixed']):
                    hits.append((tier(path, s_rels), path, line, name))
        except P.Overrun:
            return {'status': 'search_overrun', 'reason': 'regex>0.5s in ' + path, 'pattern': pat['raw'], 'candidates': []}
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    hits.sort()
    return {'status': 'ok', 'pattern': pat['raw'], 'scope_files': len(files), 'matched': len(hits), 'candidates': [[h[1], h[3]] for h in hits[:TOP]]}


def b2(pair, uni):
    ids = sorted(P.idents(P.seed_lines(pair['seed'])))
    if not ids:
        return {'status': 'no_identifiers', 'candidates': []}
    df = {}
    out = P.git('grep', '-o', '-w', '-E', '(%s)' % '|'.join(map(re.escape, ids)), pair['seed'], '--', '*.c', '*.h').stdout.decode('utf-8', 'replace')
    for line in out.splitlines():
        parts = line.split(':', 2)
        if len(parts) == 3:
            df.setdefault(parts[2], set()).add(parts[1])
    rare = [k for _, k in sorted((len(v), k) for k, v in df.items())[:3]]
    scored = []
    for path, text in P.read_files(pair['seed'], uni).items():
        if not any(r in text for r in rare):
            continue
        for name, line, body in P.functions(text):
            k = sum(1 for r in rare if re.search(r'\b%s\b' % re.escape(r), body))
            if k >= 2:
                scored.append((-k, path, line, name))
    scored.sort()
    return {'status': 'ok', 'rare': rare, 'candidates': [[p, n] for _, p, _, n in scored[:TOP]]}


def b3(pair, uni, s_rels):
    files = [p for p in uni if rel(p) in s_rels]
    fallback = not files
    if fallback:
        dirs = {rel_dir(r) for r in s_rels}
        files = [p for p in uni if rel(p) is not None and rel_dir(rel(p)) in dirs]
    names = {fn for _, fn in changed_functions(pair['seed'])}
    ids = P.idents(P.seed_lines(pair['seed']))
    scored = []
    for path, text in P.read_files(pair['seed'], files).items():
        for name, line, body in P.functions(text):
            scored.append((name not in names, -len(ids & set(re.findall(r'\b[A-Za-z_]\w*\b', body))), path, line, name))
    scored.sort()
    return {'status': 'ok', 'fallback_dir': fallback, 'files': len(files), 'candidates': [[s[2], s[4]] for s in scored[:TOP]]}


def main():
    target = HERE / 'p1prime_results.json'
    audit = HERE / 'audit_first20.json'
    if target.exists():
        raise SystemExit('preserve')
    if not audit.exists():
        raise SystemExit('blind audit (audit_first20.json) must be written before scoring')
    sample = json.loads((ROUND / 'p1prime_sample.json').read_text())['sample']
    rows = []
    for n, pair in enumerate(sample, 1):
        s_files = seed_files(pair['seed'])
        s_rels = {rel(f) for f in s_files if rel(f)}
        uni = universe(P.tree_files(pair['seed']), s_files)
        call = CALLS / ('p1p_%02d' % n)
        receipt = json.loads((call / 'receipt.json').read_text(encoding='utf-8')) if (call / 'receipt.json').exists() else {}
        delivered = receipt.get('status') == 'complete_final_received'
        res_m5 = m5(pair, uni, s_rels, (call / 'final.md').read_text(encoding='utf-8')) if delivered else {'status': 'delivery_' + str(receipt.get('status')), 'candidates': []}
        res_b2, res_b3 = b2(pair, uni), b3(pair, uni, s_rels)
        targets = {tuple(x) for x in pair['t_targets']}
        hit = lambda r: any(tuple(c) in targets for c in r['candidates'])
        rows.append({'n': n, 'seed': pair['seed'], 'target': pair['target'], 'universe_files': len(uni), 'm5': res_m5, 'b2': res_b2, 'b3': res_b3,
                     'hit': {'m5': hit(res_m5), 'b2': hit(res_b2), 'b3': hit(res_b3)}, 'tokens': receipt.get('visible_reported_tokens')})
        print(n, res_m5['status'], flush=True)
    col = lambda k: [r['hit'][k] for r in rows]
    recall = {k: sum(col(k)) / len(rows) for k in ('m5', 'b2', 'b3')}
    union = sum(1 for r in rows if r['hit']['m5'] or r['hit']['b3']) / len(rows)
    tests = {'m5_vs_b2': P.mcnemar(col('m5'), col('b2')), 'm5_vs_b3': P.mcnemar(col('m5'), col('b3'))}
    passed = (recall['m5'] - recall['b2'] >= 0.10 and recall['m5'] - recall['b3'] >= 0.10
              and min(tests['m5_vs_b2']['p'], tests['m5_vs_b3']['p']) < 0.05)
    statuses = {}
    for r in rows:
        statuses[r['m5']['status']] = statuses.get(r['m5']['status'], 0) + 1
    summary = {'pairs': len(rows), 'recall_at_20': recall, 'm5_or_b3': union, 'mcnemar': tests, 'p1prime_passed': passed,
               'm5_status': statuses, 'tokens': sum(r['tokens'] or 0 for r in rows),
               'audit_sha256': hashlib.sha256(audit.read_bytes()).hexdigest()}
    target.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
