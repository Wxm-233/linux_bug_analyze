"""P1' feasibility (criteria.md): funnel counts over the P0b held-out pool minus the 124 pairs P1 examined. WSL; no model calls.
Output: feasibility.json (counts; cross-file pairs keep hashes and targets only). Prints counts only.
"""
from pathlib import Path
import json
import random
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
sys.path.insert(0, str(INNER))
sys.path.insert(0, str(HERE.parent / 'p1_20261029'))
from linux_bug_analyze.candidate_bridge import function_spans  # noqa: E402
from linux_bug_analyze.check_families import _without_directives  # noqa: E402
from select_p1 import changed_functions  # noqa: E402

REPO = '/root/repos/linux'
P1_EXAMINED = 124
FIX_WORDS = re.compile(r'fix|bug|leak|overflow|underflow|crash|race|deadlock|corrupt|wrong|incorrect|missing|avoid|prevent|uninitiali|null|oops|panic|hang', re.I)
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def blobs(specs):
    """Contents of 'rev:path' specs via one cat-file --batch; missing ones are absent."""
    if not specs:
        return {}
    data = subprocess.run(['git', '-C', REPO, 'cat-file', '--batch'], input=''.join(s + '\n' for s in specs).encode(),
                          capture_output=True).stdout
    out, pos = {}, 0
    for s in specs:
        nl = data.index(b'\n', pos)
        header = data[pos:nl].split()
        pos = nl + 1
        if len(header) < 3 or header[1] != b'blob':
            continue
        size = int(header[2])
        out[s] = data[pos:pos + size].decode('utf-8', 'replace')
        pos += size + 1
    return out


def spans(text):
    return [(s, e, h) for s, e, h in function_spans(_without_directives(text)) if h]


def body_targets(t, s):
    """(file, function) edited inside an existing function body at T's parent, and present with a body at snapshot S."""
    hunks, path = {}, None
    for line in git('show', '--format=', '-U0', '--no-renames', t).splitlines():
        if line.startswith('--- '):
            path = line[6:] if line.startswith('--- a/') and line.endswith(('.c', '.h')) else None
        elif path and (m := HUNK.match(line)):
            hunks.setdefault(path, []).append((int(m.group(1)), int(m.group(2) or 1)))
    files = sorted(hunks)
    parent = blobs(['%s^:%s' % (t, f) for f in files])
    snap = blobs(['%s:%s' % (s, f) for f in files])
    out = set()
    for f in files:
        if '%s^:%s' % (t, f) not in parent or '%s:%s' % (s, f) not in snap:
            continue
        sp = spans(parent['%s^:%s' % (t, f)])
        at_s = {h for _, _, h in spans(snap['%s:%s' % (s, f)])}
        for a, b in hunks[f]:
            lines = [a] if b == 0 else range(a, a + b)
            for st, en, h in sp:
                inside = (st <= a < en) if b == 0 else any(st < l < en for l in lines)
                if inside and h in at_s:
                    out.add((f, h))
    return out


def arch_of(f):
    m = re.match(r'arch/([^/]+)/', f)
    return m.group(1) if m else None


def main():
    target = HERE / 'feasibility.json'
    if target.exists():
        raise SystemExit('preserve')
    held = json.loads((HERE.parent / 'p0b_20261029' / 'pairs_b.json').read_text())['held_out']
    order = sorted(held, key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(order)
    pool = order[P1_EXAMINED:]
    keys = ['pool', 'code', 'valid_target', 'not_all_seed', 'cross_file']
    funnel = dict.fromkeys(keys, 0)
    funnel['pool'] = len(pool)
    combos = dict.fromkeys(['cross_arch_dir', 'fixes_tag', 'fix_keyword', 'fix_like', 'same_series',
                            'fix_like_and_cross_arch_dir', 'fixes_tag_and_cross_arch_dir', 'fix_like_not_same_series'], 0)
    kept = []
    files_cache = {}

    def changed_files(h):
        if h not in files_cache:
            files_cache[h] = set(git('show', '--name-only', '--format=', h).split())
        return files_cache[h]

    for i, p in enumerate(pool, 1):
        s, t = p['seed'], p['target']
        sf, tf = changed_files(s), changed_files(t)
        if not (any(f.endswith(('.c', '.h')) for f in sf) and any(f.endswith(('.c', '.h')) for f in tf)):
            continue
        funnel['code'] += 1
        targets = body_targets(t, s)
        if not targets:
            continue
        funnel['valid_target'] += 1
        if targets <= changed_functions(s):
            continue
        funnel['not_all_seed'] += 1
        cross = sorted(x for x in targets if x[0] not in sf)
        if not cross:
            continue
        funnel['cross_file'] += 1
        s_arches = {arch_of(f) for f in sf} - {None}
        xarch = any(arch_of(f) and arch_of(f) not in s_arches for f, _ in cross)
        msg = git('log', '-1', '--format=%s%n%b', t)
        subject = msg.split('\n', 1)[0]
        tag = re.search(r'(?mi)^\s*Fixes:', msg) is not None
        kw = FIX_WORDS.search(subject) is not None
        fix = tag or kw
        for k, v in (('cross_arch_dir', xarch), ('fixes_tag', tag), ('fix_keyword', kw), ('fix_like', fix),
                     ('same_series', p['same_series']), ('fix_like_and_cross_arch_dir', fix and xarch),
                     ('fixes_tag_and_cross_arch_dir', tag and xarch), ('fix_like_not_same_series', fix and not p['same_series'])):
            combos[k] += bool(v)
        kept.append({'seed': s, 'target': t, 'same_series': p['same_series'], 'cross_targets': cross,
                     'cross_arch_dir': xarch, 'fixes_tag': tag, 'fix_keyword': kw})
        if i % 500 == 0:
            print('progress', i, funnel['cross_file'], flush=True)
    fix_cross = combos['fix_like']
    decision = ('register_p1prime_bug_like' if fix_cross >= 40 else
                'policy_propagation_only' if funnel['cross_file'] >= 40 else 'need_other_pair_source')
    out = {'funnel': funnel, 'cross_file_breakdown': combos, 'decision': decision, 'cross_file_pairs': kept}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({'funnel': funnel, 'cross_file_breakdown': combos, 'decision': decision}))


if __name__ == '__main__':
    main()
