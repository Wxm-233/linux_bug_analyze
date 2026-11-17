"""Candidates (criteria.md): for each Fixes-tagged commit in v6.12..END touching arch/arm64, arch/x86 or
arch/loongarch, the functions it changes in those .c files that also exist in arch/riscv at the range end, where the
RISC-V function text at the reference commit's date equals the text at the range end. Samples 30 for manual review.
WSL; no model calls. Output: samename.json.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions, END)

END, START = CK.END, 'v6.12'
REF_ARCHES = ('arm64', 'x86', 'loongarch')
GENERIC = {'init', 'setup', 'main', 'probe', 'remove', 'show', 'store', 'open', 'release', 'read', 'write', 'ioctl'}


def riscv_index():
    files = [f for f in CK.git('ls-tree', '-r', '--name-only', END, 'arch/riscv').splitlines() if f.endswith('.c')]
    idx = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for f, fns in zip(files, pool.map(lambda f: CK.functions(END, f), files)):
            for s, e, n, t in fns:
                idx.setdefault(n, []).append((f, t))
    return idx


def changed(commit, files):
    out, path = set(), None
    for line in CK.git('diff', '-U0', commit + '^', commit, '--', *files).splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
        m = re.match(r'@@ -(\d+)(?:,(\d+))? ', line)
        if m and path:
            s0, n = int(m.group(1)), int(m.group(2) or 1)
            for s, e, name, _ in CK.functions(commit + '^', path):
                if s <= s0 + max(n, 1) - 1 and s0 <= e:
                    out.add(name)
    return out


def one(sha, idx):
    try:
        files = [f for f in CK.git('show', '--no-renames', '--name-only', '--format=', sha).split()
                 if f.endswith('.c') and f.split('/')[:2] in [['arch', a] for a in REF_ARCHES]]
        if not files:
            return []
        names = {n for n in changed(sha, files) if n in idx and n not in GENERIC and not n.endswith('__init')}
        if not names:
            return []
        date = CK.git('log', '-1', '--format=%cI', sha).strip()
        rev = CK.git('rev-list', '-1', '--before=' + date, END).strip()
        rows = []
        for n in sorted(names):
            for path, end_text in idx[n]:
                then = [t for s, e, m, t in CK.functions(rev, path) if m == n] if rev else []
                if len(then) == 1 and then[0] == end_text:
                    rows.append({'ref': sha[:12], 'date': date[:10], 'arch': sorted({f.split('/')[1] for f in files}),
                                 'subject': CK.git('log', '-1', '--format=%s', sha).strip(), 'function': n,
                                 'riscv_file': path})
        return rows
    except Exception as exc:  # recorded, not retried
        return [{'ref': sha[:12], 'error': repr(exc)[:200]}]


def main():
    target = HERE / 'samename.json'
    if target.exists():
        raise SystemExit('preserve')
    idx = riscv_index()
    shas = CK.git('log', '--no-merges', '--format=%H', '--grep=Fixes:', f'{START}..{END}', '--',
                  *('arch/%s' % a for a in REF_ARCHES)).split()
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = [r for rs in pool.map(lambda s: one(s, idx), shas) for r in rs]
    errors = [r for r in rows if 'error' in r]
    cands = [r for r in rows if 'error' not in r]
    review = cands if len(cands) <= 30 else random.Random(20261102).sample(cands, 30)
    by_arch = {}
    for r in cands:
        for a in r['arch']:
            by_arch[a] = by_arch.get(a, 0) + 1
    summary = {'reference_commits': len(shas), 'candidates': len(cands), 'errors': len(errors),
               'distinct_functions': len({r['function'] for r in cands}), 'by_arch': by_arch, 'review': len(review)}
    target.write_text(json.dumps({'summary': summary, 'candidates': cands, 'review': review, 'errors': errors},
                                 indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary))
    for r in review:
        print(r['date'], r['ref'], ','.join(r['arch']), r['function'], r['riscv_file'], '|', r['subject'][:80])


if __name__ == '__main__':
    main()
