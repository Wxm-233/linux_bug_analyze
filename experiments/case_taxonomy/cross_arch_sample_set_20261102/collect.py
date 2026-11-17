"""Program fields and reading material (criteria.md sections 1, 3, 4). Source A: Fixes-tagged non-merge commits in
v6.6..END touching arch/riscv/ other than only arch/riscv/boot/dts/. Source B: Fixes-tagged non-merge commits not
touching arch/riscv/ whose message mentions riscv / RISC-V. For each: date, subject, Fixes targets and whether they
touched arch/riscv/, changed files, functions and line counts, and the dev-set flag (commit id found in the earlier
rounds' records). Reading material: dump/batch_NN.txt, 25 commits each, A before B, dev commits of A last.
WSL; no model calls. Output: items.json, dump/.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions, END)

START, END = 'v6.6', CK.END
DEV_DIRS = ['mixed_sample_llm_assist_20261101', 'mech_catalog_validation_20261102', 'mech_case_studies_20261102',
            'mech_m10_rules_20261102', 'mech_contract_model_pilot_20261102', 'mech_contract_model_pilot2_20261102',
            'mech_follow_samename_20261102']
TRAILER = re.compile(r'^(Signed-off-by|Cc|Link|Reviewed-by|Tested-by|Acked-by|Reported-by|Closes|Message-ID|'
                     r'Suggested-by|Co-developed-by|Reported-and-tested-by|Stable-dep-of|Upstream)\s*:', re.I)
MENTION = re.compile(r'risc-?v', re.I)
DIFF_LINES = 60
BATCH = 25


def log(*args):
    return CK.git('log', '--no-merges', '--format=%H', '--grep=Fixes:', f'{START}..{END}', *args).split()


def dev_ids():
    text = ''
    for d in DEV_DIRS:
        for f in (HERE.parent / d).rglob('*'):
            if f.is_file() and f.suffix in ('.json', '.md', '.py', '.txt', '.log'):
                text += f.read_text(encoding='utf-8', errors='replace')
    return set(re.findall(r'\b[0-9a-f]{12}\b', text))


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


def item(sha, source, dev):
    files = CK.git('show', '--no-renames', '--name-only', '--format=', sha).split()
    msg = CK.git('log', '-1', '--format=%B', sha)
    targets = re.findall(r'^\s*Fixes:\s*([0-9a-f]{8,40})', msg, re.M | re.I)
    tgt = []
    for t in targets:
        tf = CK.git('show', '--no-renames', '--name-only', '--format=', t).split()
        tgt.append({'commit': t[:12], 'found': bool(tf), 'touches_riscv': any(f.startswith('arch/riscv/') for f in tf)})
    stat = CK.git('show', '--numstat', '--format=', sha).split('\n')
    add = sum(int(l.split()[0]) for l in stat if l.split() and l.split()[0].isdigit())
    rem = sum(int(l.split()[1]) for l in stat if l.split() and l.split()[1].isdigit())
    return {'commit': sha[:12], 'source': source, 'dev': sha[:12] in dev,
            'date': CK.git('log', '-1', '--format=%as', sha).strip(),
            'subject': CK.git('log', '-1', '--format=%s', sha).strip(), 'fixes': tgt,
            'common_triggered': bool(tgt) and all(t['found'] and not t['touches_riscv'] for t in tgt),
            'files': files, 'functions': changed_functions(sha, files), 'added': add, 'removed': rem}


def material(it):
    sha = it['commit']
    body = [l for l in CK.git('log', '-1', '--format=%B', sha).splitlines()[1:] if not TRAILER.match(l.strip())]
    while body and not body[-1].strip():
        body.pop()
    diff = CK.git('show', '--format=', '-U2', sha, '--', '.', ':(exclude)arch/riscv/boot/dts').splitlines()
    head = [f"=== {sha} {it['source']}{' DEV' if it['dev'] else ''} {it['date']} +{it['added']}/-{it['removed']}",
            it['subject'], *[l for l in body if l.strip() or True][:40],
            'functions: ' + ', '.join(it['functions'][:12]),
            'fixes: ' + ', '.join(f"{t['commit']}{'(riscv)' if t['touches_riscv'] else '(common)'}" for t in it['fixes'])]
    if len(diff) > DIFF_LINES:
        head += CK.git('show', '--format=', '--stat=100', sha).splitlines()[-12:]
        diff = diff[:DIFF_LINES] + [f'... ({len(diff) - DIFF_LINES} more diff lines)']
    return '\n'.join(head + diff) + '\n'


def main():
    target = HERE / 'items.json'
    if target.exists():
        raise SystemExit('preserve')
    riscv_all = set(CK.git('log', '--no-merges', '--format=%H', f'{START}..{END}', '--', 'arch/riscv/').split())
    a = log('--', 'arch/riscv/', ':(exclude)arch/riscv/boot/dts')
    b = [s for s in log('-i', '--grep=risc-\\?v', '--all-match') if s not in riscv_all]
    b = [s for s in b if MENTION.search(CK.git('log', '-1', '--format=%B', s))]
    dev = dev_ids()
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(lambda x: item(*x, dev), [(s, 'A') for s in a] + [(s, 'B') for s in b]))
    items.sort(key=lambda it: (it['source'], it['dev'], it['date'], it['commit']))
    for k, it in enumerate(items):
        it['id'] = f"{it['source']}{k:03d}"
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = list(pool.map(material, items))
    (HERE / 'dump').mkdir()
    for n in range(0, len(items), BATCH):
        (HERE / 'dump' / f'batch_{n // BATCH:02d}.txt').write_text(
            ''.join(f"\n##### {it['id']}\n{t}" for it, t in zip(items[n:n + BATCH], texts[n:n + BATCH])),
            encoding='utf-8')
    target.write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    summary = {'A': len(a), 'B': len(b), 'dev_A': sum(it['dev'] for it in items if it['source'] == 'A'),
               'dev_B': sum(it['dev'] for it in items if it['source'] == 'B'),
               'batches': (len(items) + BATCH - 1) // BATCH}
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
