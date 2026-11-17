"""Method 1 (criteria.md): compare RISC-V's implementation of each common hook with the majority of the other
architectures' implementations. Steps = callees (one level of same-file expansion), kept when usable by RISC-V.
Part 1: retrospective recall over RISC-V Fixes-tagged commits (v5.10..end) that add a step to a hook implementation.
Part 2: flags at v6.6 and their fate at the range end, against minority steps. Part 3: flags at the range end and a
sample for manual review. 8 workers. WSL; no model calls. Output: consensus.json; prints summaries.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import json
import math
import random
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from linux_bug_analyze.candidate_bridge import C_WORDS  # noqa: E402
from linux_bug_analyze.sibling_pairs import NOT_FUNCTION_NAMES, named_spans  # noqa: E402

REPO = '/root/repos/linux'
END = 'df2908090cda'
SNAP = 'v6.6'
TGT = 'riscv'
HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
CALLEE = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
SKIP = C_WORDS | NOT_FUNCTION_NAMES


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


@lru_cache(maxsize=8192)
def show(rev, path):
    return git('show', '%s:%s' % (rev, path))


def file_callees(text):
    """{function name: callees incl. one level of same-file expansion} for one file."""
    lines, raw = text.splitlines(), defaultdict(set)
    for s, e, name in named_spans(text):
        raw[name] |= {c for c in CALLEE.findall('\n'.join(lines[s - 1:e])) if c not in SKIP}
    out = {}
    for name, calls in raw.items():
        exp = set(calls)
        for c in calls & set(raw):
            if c != name:
                exp |= raw[c]
        exp.discard(name)
        out[name] = exp
    return out


def arch_of(path):
    p = path.split('/')
    return p[1] if len(p) > 2 and p[0] == 'arch' else None


def impls(rev, name):
    """{arch: callees} of every architecture defining a function with this name at rev."""
    out = defaultdict(set)
    for line in git('grep', '-l', '-w', name, rev, '--', 'arch/*.c', 'arch/*.h').splitlines():
        path = line.split(':', 1)[1]
        fc = file_callees(show(rev, path))
        if name in fc:
            out[arch_of(path)] |= fc[name]
    return out


def usable(rev, names):
    names, found = sorted(names), set()
    for k in range(0, len(names), 150):
        alt = '|'.join(map(re.escape, names[k:k + 150]))
        found |= {l.split(':', 2)[-1] for l in git('grep', '-o', '-w', '-E', '(%s)' % alt, rev, '--',
                                                   'arch/%s/' % TGT, 'include/', 'mm/', 'kernel/').splitlines()}
    return found


def referenced_outside_arch(rev, names):
    names, found = sorted(names), set()
    for k in range(0, len(names), 150):
        alt = '|'.join(map(re.escape, names[k:k + 150]))
        found |= {l.split(':', 2)[-1] for l in git('grep', '-o', '-w', '-E', '(%s)' % alt, rev, '--',
                                                   '*.c', '*.h', ':!arch/', ':!tools/', ':!Documentation/').splitlines()}
    return found


def split_steps(per_arch):
    """(majority, minority) step sets over the non-target architectures."""
    others = {a: c for a, c in per_arch.items() if a != TGT}
    n = len(others)
    count = defaultdict(int)
    for calls in others.values():
        for c in calls:
            count[c] += 1
    need = max(3, math.ceil(0.5 * n))
    return {c for c, k in count.items() if k >= need}, {c for c, k in count.items() if 1 <= k <= 2}


# ---------- part 1: retrospective recall ----------

def changed_target_functions(commit):
    hunks, path = {}, None
    for line in git('show', '-U0', '--format=', '--no-renames', commit, '--', 'arch/%s/*.c' % TGT, 'arch/%s/*.h' % TGT).splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
            continue
        m = HUNK.match(line) if path else None
        if m:
            s, n = int(m.group(1)), int(m.group(2) or 1)
            hunks.setdefault(path, []).append((s, s + max(n, 1) - 1))
    out = set()
    for p, rs in hunks.items():
        for s, e, name in named_spans(show(commit, p)):
            if any(a <= e and b >= s for a, b in rs):
                out.add((p, name))
    return out


def retro_one(commit):
    try:
        parent, rows = commit + '^', []
        for path, name in sorted(changed_target_functions(commit)):
            before = file_callees(show(parent, path)).get(name)
            after = file_callees(show(commit, path)).get(name)
            if before is None or after is None:
                continue
            added = after - before
            if not added:
                continue
            per = impls(parent, name)
            if TGT not in per or len([a for a in per if a != TGT]) < 3 or not referenced_outside_arch(parent, {name}):
                continue
            use = usable(parent, added)
            majority, _ = split_steps(per)
            for c in sorted(added & use):
                rows.append({'fix': commit[:12], 'hook': name, 'step': c, 'majority_at_parent': c in majority,
                             'implementing_arches': len(per) - 1})
        return rows
    except Exception as exc:  # recorded, not retried
        return [{'fix': commit[:12], 'error': repr(exc)[:200]}]


# ---------- parts 2 and 3: snapshot index ----------

def index(rev):
    """{name: {arch: callees}} over all arch/ .c/.h files at rev."""
    files = [f for f in git('ls-tree', '-r', '--name-only', rev, 'arch').splitlines() if f.endswith(('.c', '.h'))]

    def per_file(f):
        return arch_of(f), file_callees(show(rev, f))
    out = defaultdict(lambda: defaultdict(set))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for arch, fc in pool.map(per_file, files):
            for name, calls in fc.items():
                out[name][arch] |= calls
    return out


def snapshot_flags(rev, idx):
    names = [n for n, per in idx.items() if TGT in per and len([a for a in per if a != TGT]) >= 3]
    hooks = set(names) & referenced_outside_arch(rev, set(names))
    cand_steps, rows = set(), []
    for h in hooks:
        maj, mino = split_steps(idx[h])
        cand_steps |= (maj | mino) - idx[h][TGT]
    use = usable(rev, cand_steps) if cand_steps else set()
    for h in sorted(hooks):
        maj, mino = split_steps(idx[h])
        for c in sorted((maj - idx[h][TGT]) & use):
            rows.append({'hook': h, 'step': c, 'kind': 'majority'})
        for c in sorted((mino - idx[h][TGT]) & use):
            rows.append({'hook': h, 'step': c, 'kind': 'minority'})
    return len(hooks), rows


def main():
    target = HERE / 'consensus.json'
    if target.exists():
        raise SystemExit('preserve')
    fixes = git('log', '--no-merges', '--format=%H', '--grep=Fixes:', 'v5.10..' + END, '--', 'arch/%s/' % TGT).split()
    truth = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for k, rows in enumerate(pool.map(retro_one, fixes), 1):
            truth += rows
            if k % 100 == 0:
                print('retro', k, len(fixes), flush=True)
    good = [r for r in truth if 'error' not in r]
    recall = {'entries': len(good), 'fixes': len({r['fix'] for r in good}), 'hit': sum(r['majority_at_parent'] for r in good),
              'errors': sum(1 for r in truth if 'error' in r)}
    print('recall', recall, flush=True)

    idx_snap = index(SNAP)
    n_snap, snap_rows = snapshot_flags(SNAP, idx_snap)
    print('snapshot hooks', n_snap, 'rows', len(snap_rows), flush=True)
    idx_end = index(END)
    for r in snap_rows:
        per = idx_end.get(r['hook'], {})
        r['state'] = 'gone' if TGT not in per else ('followed' if r['step'] in per[TGT] else 'open')
    rate = lambda kind: (sum(1 for r in snap_rows if r['kind'] == kind and r['state'] == 'followed'),
                         sum(1 for r in snap_rows if r['kind'] == kind and r['state'] != 'gone'))
    n_end, end_rows = snapshot_flags(END, idx_end)
    end_major = [r for r in end_rows if r['kind'] == 'majority']
    sample = random.Random(20261031).sample(end_major, min(20, len(end_major)))
    summary = {'retro': recall, 'snapshot': SNAP, 'snapshot_hooks': n_snap,
               'snapshot_followed_majority': rate('majority'), 'snapshot_followed_minority': rate('minority'),
               'end_hooks': n_end, 'end_majority_flags': len(end_major), 'end_flagged_hooks': len({r['hook'] for r in end_major})}
    target.write_text(json.dumps({'summary': summary, 'truth': truth, 'snapshot_rows': snap_rows, 'end_majority': end_major,
                                  'manual_sample': sample}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
