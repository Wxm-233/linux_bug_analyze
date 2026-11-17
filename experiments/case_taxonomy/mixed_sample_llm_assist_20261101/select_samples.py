"""Mixed sample (criteria.md): 30 buggy functions (parent of single-function RISC-V fixes in v6.6..END), their 30
fixed versions, 30 functions unchanged since v6.6, plus the special pair (huge_pte_clear at END and with
control.patch). Also runs method R (the state-size checker) on every item. WSL; no model calls.
Output: samples.json.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, show, functions, check, arch_files, DECODERS)
from linux_bug_analyze.path_conditions import analyze  # noqa: E402

END, START, RECENT = CK.END, 'v6.6', '2026-03-01'
SEED = 20261101
SKIP = re.compile(r'build|compile|warning|typo|comment|Kconfig|dts|selftest|doc|spell', re.I)
CONTEXT_LIMIT = 6000
PATCHED = '/root/work/napot_verify/src-patched/arch/riscv/mm/hugetlbpage.c'


def hunks(parent, commit):
    """[(path, old_start, old_n, new_start, new_n)] of a commit (zero-context diff)."""
    out, path = [], None
    for line in CK.git('diff', '-U0', '--no-renames', parent, commit).splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
        m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
        if m and path:
            out.append((path, int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1)))
    return out


def owner(spans, start, n):
    """Name of the single function containing lines start..start+n-1 (n=0: insertion after line start)."""
    lo, hi = start, start + max(n, 1) - 1
    names = {name for s, e, name, _ in spans if s <= lo and hi <= e}
    return names.pop() if len(names) == 1 else None


def candidate(row):
    commit, date = row
    try:
        subject = CK.git('log', '-1', '--format=%s', commit).strip()
        if SKIP.search(subject):
            return None
        parent = commit + '^'
        hs = hunks(parent, commit)
        paths = {h[0] for h in hs}
        if len(paths) != 1:
            return None
        path = paths.pop()
        if not (path.startswith('arch/riscv/') and path.endswith('.c')):
            return None
        old, new = CK.functions(parent, path), CK.functions(commit, path)
        owners_old = {owner(old, h[1], h[2]) for h in hs}
        owners_new = {owner(new, h[3], h[4]) for h in hs}
        if len(owners_old) != 1 or owners_old != owners_new or None in owners_old:
            return None
        name = owners_old.pop()
        size = sum(h[2] + h[4] for h in hs)
        o = [f for f in old if f[2] == name]
        n = [f for f in new if f[2] == name]
        if size > 30 or len(o) != 1 or len(n) != 1 or not 5 <= o[0][1] - o[0][0] + 1 <= 200:
            return None
        changed = sorted({x for h in hs for x in range(h[1], h[1] + max(h[2], 1))})
        return {'commit': commit[:12], 'date': date, 'subject': subject, 'path': path, 'function': name,
                'changed_old_lines': changed, 'changed_size': size}
    except Exception as exc:  # recorded, not retried
        return {'error': repr(exc)[:200], 'commit': commit[:12]}


def item(kind, path, rev, name):
    """Prompt material: numbered function text (file line numbers) and same-file callees."""
    spans = CK.functions(rev, path)
    (s, e, _, body), = [f for f in spans if f[2] == name]
    numbered = '\n'.join('%5d  %s' % (s + k, l) for k, l in enumerate(body.splitlines()))
    by_name = {f[2]: f for f in spans}
    ctx, used = [], 0
    for callee in dict.fromkeys(c.name for c in analyze(body)):
        if callee == name or callee not in by_name:
            continue
        cs, ce, _, ctext = by_name[callee]
        piece = '\n'.join('%5d  %s' % (cs + k, l) for k, l in enumerate(ctext.splitlines()))
        if used + len(piece) > CONTEXT_LIMIT:
            ctx.append('/* further callees truncated */')
            break
        ctx.append(piece)
        used += len(piece)
    return {'kind': kind, 'path': path, 'rev': rev, 'function': name, 'first_line': s, 'last_line': e,
            'code': numbered, 'callees': '\n\n'.join(ctx)}


def patched_item():
    raw = Path(PATCHED).read_text()
    lines = raw.splitlines()
    from linux_bug_analyze.sibling_pairs import named_spans
    from linux_bug_analyze.candidate_bridge import header_window
    spans = []
    for s, e, n in named_spans(raw):
        first = lines[s - 1]
        head = header_window(lines, s) + ' ' + first[first.index('{'):] if '{' in first else first
        spans.append((s, e, n, '\n'.join([head] + lines[s:e])))
    (s, e, _, body), = [f for f in spans if f[2] == 'huge_pte_clear']
    numbered = '\n'.join('%5d  %s' % (s + k, l) for k, l in enumerate(body.splitlines()))
    decoders = [c for c in analyze(body) if c.name in CK.DECODERS['riscv']]
    return {'kind': 'special_fixed', 'path': 'arch/riscv/mm/hugetlbpage.c', 'rev': 'control.patch',
            'function': 'huge_pte_clear', 'first_line': s, 'last_line': e, 'code': numbered, 'callees': '',
            'rule': {'flagged': False, 'sites': [], 'note': 'no decoder call left (%d)' % len(decoders)}}


def rule_result(rev, path, name, cache={}):
    if path not in CK.arch_files(rev):
        return {'flagged': False, 'sites': [], 'note': 'outside checker scope'}
    if rev not in cache:
        cache[rev] = CK.check(rev, 'riscv')
    sites = [r for r in cache[rev] if r['file'] == path and r['function'] == name]
    return {'flagged': any(r['verdict'] in ('strong', 'weak') for r in sites),
            'sites': [{k: r.get(k) for k in ('line', 'decoder', 'verdict', 'callers')} for r in sites]}


def unchanged_functions(path):
    old = {}
    for s, e, n, t in CK.functions(START, path):
        old.setdefault(n, []).append(t)
    out = []
    for s, e, n, t in CK.functions(END, path):
        if len(old.get(n, [])) == 1 and old[n][0] == t and 8 <= e - s + 1 <= 150:
            out.append(n)
    return out


def main():
    target = HERE / 'samples.json'
    if target.exists():
        raise SystemExit('preserve')
    rows = [l.split() for l in CK.git('log', '--no-merges', '--format=%H %as', '--grep=Fixes:',
                                      f'{START}..{END}', '--', 'arch/riscv/').splitlines()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        cands = [c for c in pool.map(candidate, rows) if c]
    errors = [c for c in cands if 'error' in c]
    cands = [c for c in cands if 'error' not in c]
    rnd = random.Random(SEED)
    recent = sorted([c for c in cands if c['date'] >= RECENT], key=lambda c: c['commit'])
    older = sorted([c for c in cands if c['date'] < RECENT], key=lambda c: c['commit'])
    pick = rnd.sample(recent, min(15, len(recent)))
    pick += rnd.sample(older, min(30 - len(pick), len(older)))
    items = []
    for k, c in enumerate(pick):
        pos = item('positive', c['path'], c['commit'] + '^', c['function'])
        pair = item('paired_negative', c['path'], c['commit'], c['function'])
        for it in (pos, pair):
            it.update(fix=c, group='recent' if c['date'] >= RECENT else 'older', pair=k)
        items += [pos, pair]
    pos_files = sorted({c['path'] for c in pick})
    taken = {(c['path'], c['function']) for c in pick}
    pool_first = [(p, n) for p in pos_files for n in unchanged_functions(p) if (p, n) not in taken]
    plain = rnd.sample(pool_first, min(30, len(pool_first)))
    if len(plain) < 30:
        files = [f for f in CK.git('ls-tree', '-r', '--name-only', END, 'arch/riscv').splitlines()
                 if f.endswith('.c') and f not in pos_files]
        rest = [(p, n) for p in sorted(rnd.sample(files, min(60, len(files)))) for n in unchanged_functions(p)]
        plain += rnd.sample(rest, 30 - len(plain))
    items += [item('plain_negative', p, END, n) for p, n in plain]
    items.append(item('special_buggy', 'arch/riscv/mm/hugetlbpage.c', END, 'huge_pte_clear'))
    for it in items:
        it['rule'] = rule_result(it['rev'], it['path'], it['function'])
    items.append(patched_item())
    for k, it in enumerate(items):
        it['id'] = 'S%03d' % k
    summary = {'fix_commits': len(rows), 'candidates': len(cands), 'candidate_errors': len(errors),
               'recent_candidates': len(recent), 'older_candidates': len(older),
               'positives': sum(i['kind'] == 'positive' for i in items),
               'recent_positives': sum(i['kind'] == 'positive' and i['group'] == 'recent' for i in items),
               'plain_from_positive_files': sum(1 for p, n in plain if p in pos_files),
               'plain_negatives': len(plain), 'rule_flagged': [i['id'] for i in items if i['rule']['flagged']]}
    target.write_text(json.dumps({'summary': summary, 'candidates': cands, 'errors': errors, 'items': items},
                                 indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
