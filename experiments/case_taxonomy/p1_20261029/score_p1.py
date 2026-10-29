"""P1 instantiation, baselines and scoring (registration_p1.md sections 3-5). WSL; no model calls (reads saved final.md).
Output: p1_results.json. Prints the summary only.
"""
from pathlib import Path
import fnmatch
import json
import math
import re
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
CALLS = INNER.parent / '模型调用测试' / '2026-10-29'
sys.path.insert(0, str(INNER))
from linux_bug_analyze.candidate_bridge import C_WORDS, function_spans  # noqa: E402
from linux_bug_analyze.check_families import _without_directives  # noqa: E402

REPO = '/root/repos/linux'
TOP, MAX_FILES, FILE_SECONDS = 20, 50_000, 0.5


class Overrun(Exception):
    pass


def _alarm(signum, frame):
    raise Overrun()


signal.signal(signal.SIGALRM, _alarm)


def git(*args, inp=None):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True, input=inp)


def tree_files(rev):
    return [p for p in git('ls-tree', '-r', '--name-only', rev).stdout.decode('utf-8', 'replace').splitlines() if p.endswith(('.c', '.h'))]


def read_files(rev, paths):
    """Contents of many blobs at ``rev`` via one cat-file --batch."""
    if not paths:
        return {}
    proc = subprocess.run(['git', '-C', REPO, 'cat-file', '--batch'], input=''.join('%s:%s\n' % (rev, p) for p in paths).encode(), capture_output=True)
    data, out, pos = proc.stdout, {}, 0
    for p in paths:
        nl = data.index(b'\n', pos)
        header = data[pos:nl].split()
        pos = nl + 1
        if len(header) < 3 or header[1] != b'blob':
            continue
        size = int(header[2])
        out[p] = data[pos:pos + size].decode('utf-8', 'replace')
        pos += size + 1
    return out


def functions(text):
    plain = _without_directives(text)
    lines = plain.splitlines()
    return [(h, s, '\n'.join(lines[s - 1:e])) for s, e, h in function_spans(plain) if h]


def glob_regex(g):
    out, i = '', 0
    while i < len(g):
        if g.startswith('**', i):
            out += '.*'
            i += 2
        elif g[i] == '*':
            out += '[^/]*'
            i += 1
        elif g[i] == '?':
            out += '[^/]'
            i += 1
        else:
            out += re.escape(g[i])
            i += 1
    return re.compile('^' + out + '$')


def rank_key(path, line, seed_files):
    seed_dirs = {f.rsplit('/', 1)[0] for f in seed_files if '/' in f}
    tier = 0 if path in seed_files else 1 if path.rsplit('/', 1)[0] in seed_dirs else 2
    return (tier, path, line)


def seed_lines(seed):
    diff = git('show', '--format=', '-U0', seed).stdout.decode('utf-8', 'replace')
    return [l[1:] for l in diff.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---'))]


def idents(lines):
    return {t for l in lines for t in re.findall(r'\b[A-Za-z_]\w*\b', l) if t not in C_WORDS and len(t) >= 4}


def parse_pattern(final_text):
    try:
        obj = json.loads(final_text[final_text.find('{'):final_text.rfind('}') + 1])
        scope, match, fixed = obj['scope'], obj['match'], obj.get('fixed', [])
        assert isinstance(scope, list) and 1 <= len(scope) <= 5 and all(isinstance(x, str) and x for x in scope)
        assert isinstance(match, list) and 1 <= len(match) <= 5 and isinstance(fixed, list) and len(fixed) <= 5
        return {'scope': scope, 'match': [re.compile(m) for m in match], 'fixed': [re.compile(f) for f in fixed],
                'raw': {'scope': scope, 'match': match, 'fixed': fixed, 'rationale': obj.get('rationale')}}
    except Exception as exc:  # noqa: BLE001 - any malformed output is "pattern invalid"
        return {'error': repr(exc)[:200]}


def m5(pair, all_files, final_text):
    pat = parse_pattern(final_text)
    if 'error' in pat:
        return {'status': 'pattern_invalid', 'error': pat['error'], 'candidates': []}
    globs = [glob_regex(g) for g in pat['scope']]
    files = [p for p in all_files if any(g.match(p) for g in globs)]
    if len(files) > MAX_FILES:
        return {'status': 'search_overrun', 'reason': 'files>%d' % MAX_FILES, 'pattern': pat['raw'], 'candidates': []}
    excluded = {tuple(x) for x in pair['s_changed']}
    seed_files = {f for f, _ in excluded} | {f for f in git('show', '--name-only', '--format=', pair['seed']).stdout.decode().split()}
    hits = []
    for path, text in read_files(pair['seed'], files).items():
        signal.setitimer(signal.ITIMER_REAL, FILE_SECONDS)
        try:
            for name, line, body in functions(text):
                if (path, name) in excluded:
                    continue
                if all(r.search(body) for r in pat['match']) and not any(r.search(body) for r in pat['fixed']):
                    hits.append((path, name, line))
        except Overrun:
            return {'status': 'search_overrun', 'reason': 'regex>0.5s in ' + path, 'pattern': pat['raw'], 'candidates': []}
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    hits.sort(key=lambda h: rank_key(h[0], h[2], seed_files))
    return {'status': 'ok', 'pattern': pat['raw'], 'scope_files': len(files), 'matched': len(hits), 'candidates': [[h[0], h[1]] for h in hits[:TOP]]}


def b1(pair):
    excluded = {tuple(x) for x in pair['s_changed']}
    seed_files = [f for f in git('show', '--name-only', '--format=', pair['seed']).stdout.decode().split() if f.endswith(('.c', '.h'))]
    ids = idents(seed_lines(pair['seed']))
    scored = []
    for path, text in read_files(pair['seed'], seed_files).items():
        for name, line, body in functions(text):
            if (path, name) not in excluded:
                scored.append((-len(ids & set(re.findall(r'\b[A-Za-z_]\w*\b', body))), path, line, name))
    scored.sort()
    return {'status': 'ok', 'candidates': [[p, n] for _, p, _, n in scored[:TOP]]}


def b2(pair, all_files):
    excluded = {tuple(x) for x in pair['s_changed']}
    seed_files = [f for f in git('show', '--name-only', '--format=', pair['seed']).stdout.decode().split() if f.endswith(('.c', '.h'))]
    ids = sorted(idents(seed_lines(pair['seed'])))
    if not ids:
        return {'status': 'no_identifiers', 'candidates': []}
    df = {}
    out = git('grep', '-o', '-w', '-E', '(%s)' % '|'.join(map(re.escape, ids)), pair['seed'], '--', '*.c', '*.h').stdout.decode('utf-8', 'replace')
    for line in out.splitlines():
        parts = line.split(':', 2)
        if len(parts) == 3:
            df.setdefault(parts[2], set()).add(parts[1])
    rare = sorted((len(v), k) for k, v in df.items())[:3]
    rare = [k for _, k in rare]
    dirs = {f.rsplit('/', 1)[0] for f in seed_files if '/' in f}
    files = [p for p in all_files if any(p.startswith(d + '/') for d in dirs)]
    scored = []
    for path, text in read_files(pair['seed'], files).items():
        for name, line, body in functions(text):
            if (path, name) in excluded:
                continue
            k = sum(1 for r in rare if re.search(r'\b%s\b' % re.escape(r), body))
            if k >= 2:
                scored.append((-k, path, line, name))
    scored.sort()
    return {'status': 'ok', 'rare': rare, 'candidates': [[p, n] for _, p, _, n in scored[:TOP]]}


def mcnemar(a, b):
    """Exact two-sided McNemar on paired hit lists."""
    x = sum(1 for p, q in zip(a, b) if p and not q)
    y = sum(1 for p, q in zip(a, b) if q and not p)
    n = x + y
    if n == 0:
        return {'a_only': x, 'b_only': y, 'p': 1.0}
    k = min(x, y)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {'a_only': x, 'b_only': y, 'p': p}


def main():
    target = HERE / 'p1_results.json'
    if target.exists():
        raise SystemExit('preserve')
    sample = json.loads((HERE / 'p1_sample.json').read_text())['sample']
    rows = []
    for n, pair in enumerate(sample, 1):
        all_files = tree_files(pair['seed'])
        call = CALLS / ('p1_%02d' % n)
        receipt = json.loads((call / 'receipt.json').read_text(encoding='utf-8')) if (call / 'receipt.json').exists() else {}
        delivered = receipt.get('status') == 'complete_final_received'
        res_m5 = m5(pair, all_files, (call / 'final.md').read_text(encoding='utf-8')) if delivered else {'status': 'delivery_' + str(receipt.get('status')), 'candidates': []}
        res_b1, res_b2 = b1(pair), b2(pair, all_files)
        targets = {tuple(x) for x in pair['t_targets']}
        hit = lambda r: any(tuple(c) in targets for c in r['candidates'])
        rows.append({'n': n, 'seed': pair['seed'], 'target': pair['target'], 'm5': res_m5, 'b1': res_b1, 'b2': res_b2,
                     'hit': {'m5': hit(res_m5), 'b1': hit(res_b1), 'b2': hit(res_b2)}, 'tokens': receipt.get('visible_reported_tokens')})
        print(n, res_m5['status'], rows[-1]['hit'], flush=True)
    col = lambda k: [r['hit'][k] for r in rows]
    recall = {k: sum(col(k)) / len(rows) for k in ('m5', 'b1', 'b2')}
    union = sum(1 for r in rows if r['hit']['m5'] or r['hit']['b1']) / len(rows)
    tests = {'m5_vs_b1': mcnemar(col('m5'), col('b1')), 'm5_vs_b2': mcnemar(col('m5'), col('b2'))}
    passed = (recall['m5'] - recall['b1'] >= 0.10 and recall['m5'] - recall['b2'] >= 0.10
              and min(tests['m5_vs_b1']['p'], tests['m5_vs_b2']['p']) < 0.05)
    statuses = {}
    for r in rows:
        statuses[r['m5']['status']] = statuses.get(r['m5']['status'], 0) + 1
    summary = {'pairs': len(rows), 'recall_at_20': recall, 'm5_or_b1': union, 'mcnemar': tests, 'p1_passed': passed, 'm5_status': statuses,
               'tokens': sum(r['tokens'] or 0 for r in rows)}
    target.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
