"""Design-time estimate on the DEV set only (no model): pair each fixed RISC-V file with reference files by path
role at fix^, list identifiers the reference has and RISC-V lacks, keep those in a fix-idiom catalog mined from
reference-arch Fixes commits dated before the fix, and check whether the fix's added identifiers are among them."""
import json, re, subprocess, sys
from collections import Counter
from functools import lru_cache

REPO = '/root/repos/linux'
BASE, OUT = sys.argv[1], sys.argv[2]
REF = ('arm64', 'x86', 'loongarch')
ID = re.compile(r'[A-Za-z_]\w{2,}')
STRIP = re.compile(r'/\*.*?\*/|//[^\n]*', re.S)


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def idents(text):
    return set(ID.findall(STRIP.sub(' ', text)))


@lru_cache(maxsize=None)
def tree(rev):
    return git('ls-tree', '-r', '--name-only', rev, 'arch/').splitlines()


def catalog(before):
    """identifier -> number of reference-arch Fixes commits (3 years before `before`) that add it."""
    log = git('log', '--format=@@%H', '-U0', '--grep=Fixes:', f'--before={before}', '--since=3 years ago',
              '--', *[f'arch/{a}' for a in REF])
    cnt, plus, minus = Counter(), set(), set()
    for l in log.splitlines() + ['@@end']:
        if l.startswith('@@') and len(l) > 2 and not l.startswith('@@ '):
            cnt.update(plus - minus)
            plus, minus = set(), set()
        elif l.startswith('+') and not l.startswith('+++'):
            plus |= idents(l[1:])
        elif l.startswith('-') and not l.startswith('---'):
            minus |= idents(l[1:])
    return cnt


def siblings(rev, f):
    rel = f.split('/', 2)[2]
    top, stem = rel.split('/')[0], re.sub(r'\W.*', '', rel.rsplit('/', 1)[-1])[:4]
    out = []
    for p in tree(rev):
        parts = p.split('/', 2)
        if len(parts) < 3 or parts[1] not in REF or not p.endswith(('.c', '.h', '.S', 'Makefile')):
            continue
        r = parts[2]
        if r == rel:
            out.append((p, 'same_subpath'))
        elif r.split('/')[0] == top and r.rsplit('/', 1)[-1][:4] == stem:
            out.append((p, 'same_dir_similar_name'))
    return out


labels = json.load(open(f'{BASE}/cross_arch_sample_set_20261102/labels_v2_1.json', encoding='utf-8'))
dev = [r for r in labels if r['dev'] and r['cross'] == 'C' and r['flag'] not in ('无关', '构建错误')]
rows, cats = [], {}
COMMON = set(ID.findall(git('grep', '-h', '-o', '-E', '[A-Za-z_][A-Za-z0-9_]{2,}', 'v6.12', '--', 'include/linux', 'include/asm-generic')))
print('common ids', len(COMMON))
for r in dev:
    sha, rev = r['commit'], r['commit'] + '^'
    year = r['date'][:4]
    if year not in cats:
        cats[year] = catalog(f'{year}-01-01')
    cat = cats[year]
    diff = git('show', '--format=', '-U0', sha, '--', 'arch/riscv')
    plus = {x for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++') for x in idents(l[1:])}
    minus = {x for l in diff.splitlines() if l.startswith('-') and not l.startswith('---') for x in idents(l[1:])}
    added = plus - minus
    best, n_cand, pairs = None, 0, 0
    for f in [f for f in r['files'] if f.startswith('arch/riscv')]:
        mine = idents(git('show', f'{rev}:{f}'))
        for p, how in siblings(rev, f):
            pairs += 1
            ref_ids = idents(git('show', f'{rev}:{p}'))
            arches = {q.split('/')[1] for q, _ in siblings(rev, f) if q.rsplit('/', 1)[-1] == p.rsplit('/', 1)[-1]}
            cons = Counter(x for q, _ in siblings(rev, f) for x in idents(git('show', f'{rev}:{q}')) - mine)
            cand = sorted(((cons[x], cat[x], x) for x in ref_ids - mine if x in COMMON),
                          reverse=True)
            n_cand += len(cand)
            for rank, (_, c, x) in enumerate(cand, 1):
                if x in added and (best is None or rank < best['rank']):
                    best = {'file': f, 'ref': p, 'how': how, 'idiom': x, 'catalog_count': c, 'rank': rank,
                            'of': len(cand)}
    rows.append({'id': r['id'], 'mech': r['mechanism'], 'kind': r['counterpart_kind'], 'pairs': pairs,
                 'candidates': n_cand, 'located': best})
json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
loc = [x for x in rows if x['located']]
print('dev', len(rows), 'located', len(loc), 'top10', sum(x['located']['rank'] <= 10 for x in loc), 'top20', sum(x['located']['rank'] <= 20 for x in loc),
      'median candidates/case', sorted(x['candidates'] for x in rows)[len(rows) // 2])
for x in rows:
    print(x['id'], x['mech'], x['kind'], x['pairs'], x['candidates'], x['located'] and
          (x['located']['idiom'], x['located']['rank'], x['located']['of'], x['located']['how']))
