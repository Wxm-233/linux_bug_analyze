"""Program fields and reading material (criteria.md sections 1 and 2). Source R: Fixes-tagged non-merge commits in
v6.1..v6.6 touching arch/riscv/ other than only arch/riscv/boot/dts/. Source L: Fixes-tagged non-merge commits in
v6.6..END touching arch/loongarch/ other than only arch/loongarch/boot/dts/ (a commit already in R is not repeated).
Commits whose 12-character id appears in any earlier record under experiments/case_taxonomy/ are excluded, except
the raw candidate lists of unified_impl_stage1_20261027 (criteria_amendment1.md). For each
kept commit: date, subject, Fixes targets, changed files, functions and line counts. Reading material:
dump/batch_NN.txt, 25 commits each. WSL; no model calls. Output: items.json, excluded.json, dump/.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions, END)

SOURCES = [('R', 'v6.1', 'v6.6', 'arch/riscv/'), ('L', 'v6.6', CK.END, 'arch/loongarch/')]
TRAILER = re.compile(r'^(Signed-off-by|Cc|Link|Reviewed-by|Tested-by|Acked-by|Reported-by|Closes|Message-ID|'
                     r'Suggested-by|Co-developed-by|Reported-and-tested-by|Stable-dep-of|Upstream)\s*:', re.I)
SUFFIXES = ('.json', '.md', '.py', '.txt', '.log', '.csv', '.sh', '.patch')
DIFF_LINES = 60
BATCH = 25


def log(start, end, path):
    return CK.git('log', '--no-merges', '--format=%H', '--grep=Fixes:', f'{start}..{end}', '--', path,
                  f':(exclude){path}boot/dts').split()


def raw_pool(f):
    """criteria_amendment1.md: program-generated candidate lists nobody read are not records of use."""
    return f.parent.name != 'fix_strategy_test_20261105' and 'unified_impl_stage1_20261027' in f.parts         and 'candidates' in f.name and f.suffix == '.txt'


def seen_ids():
    found = set()
    for f in HERE.parent.rglob('*'):
        if f.is_file() and f.suffix in SUFFIXES and HERE not in f.parents and not raw_pool(f):
            found |= set(re.findall(r'\b[0-9a-f]{12}', f.read_text(encoding='utf-8', errors='replace')))
    return found


def changed_functions(sha, files):
    out = []
    for f in files:
        if not f.endswith('.c'):
            continue
        for line in CK.git('diff', '-U0', sha + '^', sha, '--', f).splitlines():
            m = re.match(r'@@ -(\d+)(?:,(\d+))? ', line)
            if m:
                s0, n = int(m.group(1)), int(m.group(2) or 1)
                for s, e, name, _ in CK.functions(sha + '^', f):
                    if s <= s0 + max(n, 1) - 1 and s0 <= e and (f, name) not in out:
                        out.append((f, name))
    return [f'{f}:{n}' for f, n in out]


def item(sha, source):
    files = CK.git('show', '--no-renames', '--name-only', '--format=', sha).split()
    msg = CK.git('log', '-1', '--format=%B', sha)
    tgt = [t[:12] for t in re.findall(r'^\s*Fixes:\s*([0-9a-f]{8,40})', msg, re.M | re.I)]
    stat = CK.git('show', '--numstat', '--format=', sha).split('\n')
    add = sum(int(l.split()[0]) for l in stat if l.split() and l.split()[0].isdigit())
    rem = sum(int(l.split()[1]) for l in stat if l.split() and l.split()[1].isdigit())
    return {'commit': sha[:12], 'source': source, 'date': CK.git('log', '-1', '--format=%as', sha).strip(),
            'subject': CK.git('log', '-1', '--format=%s', sha).strip(), 'fixes': tgt, 'files': files,
            'functions': changed_functions(sha, files), 'added': add, 'removed': rem}


def material(it):
    sha = it['commit']
    body = [l for l in CK.git('log', '-1', '--format=%B', sha).splitlines()[1:] if not TRAILER.match(l.strip())]
    while body and not body[-1].strip():
        body.pop()
    diff = CK.git('show', '--format=', '-U2', sha, '--', '.', ':(exclude)arch/riscv/boot/dts',
                  ':(exclude)arch/loongarch/boot/dts').splitlines()
    head = [f"=== {sha} {it['source']} {it['date']} +{it['added']}/-{it['removed']}", it['subject'], *body[:40],
            'functions: ' + ', '.join(it['functions'][:12]), 'fixes: ' + ', '.join(it['fixes'])]
    if len(diff) > DIFF_LINES:
        head += CK.git('show', '--format=', '--stat=100', sha).splitlines()[-12:]
        diff = diff[:DIFF_LINES] + [f'... ({len(diff) - DIFF_LINES} more diff lines)']
    return '\n'.join(head + diff) + '\n'


def main():
    if (HERE / 'items.json').exists():
        raise SystemExit('preserve')
    seen = seen_ids()
    picked, excluded, taken = [], [], set()
    for source, start, end, path in SOURCES:
        for sha in log(start, end, path):
            if sha in taken:
                continue
            taken.add(sha)
            (excluded if sha[:12] in seen else picked).append((sha, source))
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(lambda x: item(*x), picked))
    items.sort(key=lambda it: (it['source'] != 'R', it['date'], it['commit']))
    for k, it in enumerate(items):
        it['id'] = f"{it['source']}{k:03d}"
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = list(pool.map(material, items))
    (HERE / 'dump').mkdir()
    for n in range(0, len(items), BATCH):
        (HERE / 'dump' / f'batch_{n // BATCH:02d}.txt').write_text(
            ''.join(f"\n##### {it['id']}\n{t}" for it, t in zip(items[n:n + BATCH], texts[n:n + BATCH])),
            encoding='utf-8')
    (HERE / 'items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'excluded.json').write_text(json.dumps([{'commit': s[:12], 'source': src} for s, src in excluded],
                                                   indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'kept': {s: sum(it['source'] == s for it in items) for s in 'RL'},
                      'excluded': {s: sum(src == s for _, src in excluded) for s in 'RL'},
                      'batches': (len(items) + BATCH - 1) // BATCH}))


if __name__ == '__main__':
    main()
