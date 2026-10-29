"""Candidate coverage on the P1' dev set (criteria.md): B3 structural correspondence vs interface users (API). WSL; no model calls.
Output: coverage.json (per-pair booleans and pool sizes only). Prints the summary only.
"""
from pathlib import Path
import json
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'p1prime_20261029' / 'run'))
import score_p1prime as S  # noqa: E402

P = S.P
MAX_DF = 500
WORD = re.compile(r'\b[A-Za-z_]\w*\b')


def b3_full(pair, uni, s_rels, texts):
    files = [p for p in uni if S.rel(p) in s_rels]
    if not files:
        dirs = {S.rel_dir(r) for r in s_rels}
        files = [p for p in uni if S.rel(p) is not None and S.rel_dir(S.rel(p)) in dirs]
    names = {fn for _, fn in S.changed_functions(pair['seed'])}
    ids = P.idents(P.seed_lines(pair['seed']))
    scored = []
    for path in files:
        for name, line, body in P.functions(texts.get(path, '')):
            scored.append((name not in names, -len(ids & set(WORD.findall(body))), path, line, name))
    scored.sort()
    return [(s[2], s[4]) for s in scored]


def generic_ids(pair):
    ids = sorted(P.idents(P.seed_lines(pair['seed'])))
    if not ids:
        return {}
    out = P.git('grep', '-o', '-w', '-E', '(%s)' % '|'.join(map(re.escape, ids)), pair['seed'], '--', '*.c', '*.h').stdout.decode('utf-8', 'replace')
    files = {}
    for line in out.splitlines():
        parts = line.split(':', 2)
        if len(parts) == 3:
            files.setdefault(parts[2], set()).add(parts[1])
    return {k: len(v) for k, v in files.items() if len(v) <= MAX_DF and any(not f.startswith('arch/') for f in v)}


def api_full(uni, texts, gids):
    scored = []
    for path in uni:
        text = texts.get(path, '')
        if not any(g in text for g in gids):
            continue
        for name, line, body in P.functions(text):
            found = set(WORD.findall(body)) & set(gids)
            if found:
                scored.append((-len(found), min(gids[g] for g in found), path, line, name))
    scored.sort()
    return [(s[2], s[4]) for s in scored]


def main():
    target = HERE / 'coverage.json'
    if target.exists():
        raise SystemExit('preserve')
    sample = json.loads((C / 'p1prime_20261029' / 'p1prime_sample.json').read_text())['sample']
    rows = []
    for n, pair in enumerate(sample, 1):
        s_files = S.seed_files(pair['seed'])
        s_rels = {S.rel(f) for f in s_files if S.rel(f)}
        uni = S.universe(P.tree_files(pair['seed']), s_files)
        texts = P.read_files(pair['seed'], uni)
        b3, gids = b3_full(pair, uni, s_rels, texts), generic_ids(pair)
        api = api_full(uni, texts, gids)
        tg = {tuple(x) for x in pair['t_targets']}
        cov = lambda cands: any(c in tg for c in cands)
        rows.append({'n': n, 'b3_20': cov(b3[:20]), 'b3_40': cov(b3[:40]), 'b3_all': cov(b3), 'api_20': cov(api[:20]), 'api_40': cov(api[:40]),
                     'api_all': cov(api), 'union_20_20': cov(b3[:20] + api[:20]), 'union_all': cov(b3 + api),
                     'b3_pool': len(b3), 'api_pool': len(api), 'generic_ids': len(gids)})
        print(n, flush=True)
    keys = ['b3_20', 'b3_40', 'b3_all', 'api_20', 'api_40', 'api_all', 'union_20_20', 'union_all']
    covered = {k: sum(r[k] for r in rows) for k in keys}
    b3_miss = [r for r in rows if not r['b3_20']]
    pool = lambda k: {'median': statistics.median(r[k] for r in rows), 'max': max(r[k] for r in rows), 'zero': sum(r[k] == 0 for r in rows)}
    summary = {'pairs': len(rows), 'covered': covered, 'b3_20_reproduces_p1prime_26': covered['b3_20'] == 26,
               'on_b3_20_misses': {'pairs': len(b3_miss), 'api_20': sum(r['api_20'] for r in b3_miss), 'api_40': sum(r['api_40'] for r in b3_miss),
                                   'api_all': sum(r['api_all'] for r in b3_miss)},
               'pool_size': {'b3': pool('b3_pool'), 'api': pool('api_pool')}, 'generic_ids': pool('generic_ids'),
               'unreachable_by_both_pools': sum(not r['union_all'] for r in rows),
               'reading': {'union_20_20_ge_35': covered['union_20_20'] >= 35, 'api_20_adds_lt_5_on_b3_misses': sum(r['api_20'] for r in b3_miss) < 5}}
    target.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
