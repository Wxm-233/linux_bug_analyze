"""Direction 4, round 3 (criteria.md): "follow the arm64 fix" over all families.
For each Fixes-tagged commit of the source architecture (not touching the target architecture), the functions it edits
gain new callees ("new steps"); a reminder is a new step the target architecture's same-named function lacks at the
fix's parent. Outcome at the range end: followed / still open / function gone. Baseline: callees the source function
already had before the fix that the target function lacked. 8 workers. WSL; no model calls. Output: follow.json.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import json
import re
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from linux_bug_analyze.candidate_bridge import C_WORDS  # noqa: E402
from linux_bug_analyze.sibling_pairs import NOT_FUNCTION_NAMES, named_spans  # noqa: E402

REPO = '/root/repos/linux'
END = 'df2908090cda'
CONFIGS = [('arm64_to_riscv', 'arm64', 'riscv', 'v5.10'), ('x86_to_riscv', 'x86', 'riscv', 'v5.10'),
           ('arm64_to_loongarch', 'arm64', 'loongarch', 'v5.19')]
HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
CALLEE = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
SKIP = C_WORDS | NOT_FUNCTION_NAMES


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


@lru_cache(maxsize=4096)
def show(rev, path):
    return git('show', '%s:%s' % (rev, path))


def bodies(text):
    """{name: concatenated bodies} of named functions."""
    lines, out = text.splitlines(), {}
    for s, e, name in named_spans(text):
        out[name] = out.get(name, '') + '\n' + '\n'.join(lines[s - 1:e])
    return out


def callees(body, own):
    return {c for c in CALLEE.findall(body) if c not in SKIP and c != own}


def changed_functions(commit, src):
    """{(path, name)} of source-arch functions whose span contains a new-side hunk line."""
    hunks, path = {}, None
    for line in git('show', '-U0', '--format=', '--no-renames', commit, '--', 'arch/%s/*.c' % src, 'arch/%s/*.h' % src).splitlines():
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


def target_function(rev, tgt, name):
    """Callees of the target arch's same-named function(s) at rev, or None if absent."""
    files = [l.split(':', 1)[1] for l in git('grep', '-l', '-w', name, rev, '--', 'arch/%s/*.c' % tgt, 'arch/%s/*.h' % tgt).splitlines() if ':' in l]
    found, calls = False, set()
    for f in files:
        b = bodies(show(rev, f))
        if name in b:
            found = True
            calls |= callees(b[name], name)
    return (calls, files) if found else (None, files)


def usable(rev, names, tgt):
    """Names that occur in the target arch, include/, mm/ or kernel/ at rev."""
    names, out = sorted(names), set()
    for k in range(0, len(names), 150):
        alt = '|'.join(map(re.escape, names[k:k + 150]))
        out |= {l.split(':', 2)[-1] for l in git('grep', '-o', '-w', '-E', '(%s)' % alt, rev, '--', 'arch/%s/' % tgt, 'include/', 'mm/', 'kernel/').splitlines()}
    return out


def first_addition(fix, files, step):
    """(commit, has_fixes, days) of the earliest commit after the fix whose diff in files mentions step( ; approximate."""
    log = git('log', '--format=%H %ct', '--reverse', '-G', r'\b%s\s*\(' % re.escape(step), fix + '..' + END, '--', *files).splitlines()
    if not log:
        return None
    c, ct = log[0].split()
    fct = int(git('show', '-s', '--format=%ct', fix).strip() or 0)
    return {'commit': c[:12], 'has_fixes': 'Fixes:' in git('show', '-s', '--format=%B', c), 'days': round((int(ct) - fct) / 86400)}


def one(args):
    fix, src, tgt = args
    try:
        touched = git('show', '--format=', '--name-only', fix).splitlines()
        if any(p.startswith('arch/%s/' % tgt) for p in touched):
            return {'fix': fix, 'skipped': 'touches_target'}
        parent = fix + '^'
        items = []
        for path, name in sorted(changed_functions(fix, src)):
            before = bodies(show(parent, path)).get(name)
            after = bodies(show(fix, path)).get(name)
            if before is None or after is None:
                continue
            tcalls, _ = target_function(parent, tgt, name)
            if tcalls is None:
                continue
            cb, ca = callees(before, name), callees(after, name)
            new, old = ca - cb, cb
            use = usable(parent, new | old, tgt) if new | old else set()
            for kind, steps in (('new', new), ('baseline', old)):
                for s in sorted(steps & use - tcalls):
                    items.append({'func': name, 'src_path': path, 'step': s, 'kind': kind})
        return {'fix': fix, 'items': items}
    except Exception as exc:  # recorded, not retried
        return {'fix': fix, 'error': repr(exc)[:200]}


def outcome(fix, tgt, item, end_cache):
    key = item['func']
    if key not in end_cache:
        end_cache[key] = target_function(END, tgt, key)
    calls, files = end_cache[key]
    if calls is None:
        return {'state': 'gone'}
    if item['step'] in calls:
        out = {'state': 'followed'}
        if item['kind'] == 'new':
            out['first'] = first_addition(fix, files, item['step'])
        return out
    return {'state': 'open'}


def run(name, src, tgt, since):
    fixes = git('log', '--no-merges', '--format=%H', '--grep=Fixes:', since + '..' + END, '--', 'arch/%s/' % src).split()
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = []
        for k, r in enumerate(pool.map(one, [(f, src, tgt) for f in fixes]), 1):
            rows.append(r)
            if k % 200 == 0:
                print(name, 'scan', k, len(fixes), flush=True)
    end_cache = {}
    items = [(r['fix'], it) for r in rows for it in r.get('items', [])]

    def fin(pair):
        fix, it = pair
        return {**it, 'fix': fix[:12], **outcome(fix, tgt, it, end_cache)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        done = list(pool.map(fin, items))
    new = [d for d in done if d['kind'] == 'new']
    base = [d for d in done if d['kind'] == 'baseline']
    rate = lambda ds: round(sum(d['state'] == 'followed' for d in ds) / len(ds), 3) if ds else None
    fol = [d for d in new if d['state'] == 'followed' and d.get('first')]
    summary = {'fixes': len(fixes), 'skipped_touch_target': sum(1 for r in rows if r.get('skipped')),
               'errors': sum(1 for r in rows if r.get('error')), 'reminders': len(new),
               'reminder_fixes': len({d['fix'] for d in new}), 'reminder_functions': len({d['func'] for d in new}),
               'followed_rate_new': rate(new), 'followed_rate_baseline': rate(base), 'baseline_items': len(base),
               'states_new': {s: sum(d['state'] == s for d in new) for s in ('followed', 'open', 'gone')},
               'followed_by_fixes_commit': sum(1 for d in fol if d['first']['has_fixes']),
               'lag_days_median': statistics.median(d['first']['days'] for d in fol) if fol else None,
               'open_reminders': sum(d['state'] == 'open' for d in new)}
    print(name, json.dumps(summary), flush=True)
    return {'summary': summary, 'reminders': new, 'errors': [r for r in rows if r.get('error')][:20]}


def main():
    target = HERE / 'follow.json'
    if target.exists():
        raise SystemExit('preserve')
    out = {name: run(name, src, tgt, since) for name, src, tgt, since in CONFIGS}
    target.write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
