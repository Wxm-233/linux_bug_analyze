"""Architecture interface completeness, RISC-V (criteria.md). WSL; no model calls; prints counts only.
Inventory of interfaces common code lets architectures provide (K: Kconfig select of ARCH_HAS_/HAVE_/...; M: #define of
__HAVE_ARCH_/__ARCH_WANT_/ARCH_HAS_; S: self-defining marker for a common #ifndef; W: strong definition of a common __weak
function), per architecture. Gap = x86 and arm64 provide, riscv does not. Truth = riscv commits adding a provision.
Output: gaps.json, provisions.json, stats.json.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import json
import random
import re
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
sys.path.insert(0, str(C_DIR / 'sibling_dataset_20261029'))
import build_dataset as BD  # noqa: E402

X = BD.X
REPO = '/root/repos/linux'
END = X.RANGE.split('..')[1]
LTS = ['v5.10', 'v5.15', 'v6.1', 'v6.6', 'v6.12']
REFS = ('x86', 'arm64', 'powerpc', 's390')
K_PREFIX = r'(ARCH_HAS_\w+|ARCH_WANT\w*|ARCH_SUPPORTS_\w+|ARCH_USE_\w+|HAVE_\w+)'  # plain groups: also used by git grep -E
M_PREFIX = r'(__HAVE_ARCH_\w+|__ARCH_WANT_\w+|ARCH_HAS_\w+)'
K_LINE = re.compile(r'^\s*select\s+(%s)\b' % K_PREFIX)
M_LINE = re.compile(r'^\s*#\s*define\s+(%s)\b' % M_PREFIX)
S_LINE = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*$')
DEF_LINE = re.compile(r'^[A-Za-z_][^;(]*?\b([A-Za-z_]\w*)\s*\(')
GUARD = re.compile(r'#\s*ifndef\s+([A-Za-z_]\w*)|!\s*defined\s*\(?\s*([A-Za-z_]\w*)')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def grep_lines(rev, pattern, *paths, opts=('-E',)):
    """[(path, text)] of git grep matches at rev."""
    out = []
    for line in git('grep', *opts, pattern, rev, '--', *paths).splitlines():
        parts = line.split(':', 2)
        if len(parts) == 3:
            out.append((parts[1], parts[2]))
    return out


def arch_of(path):
    p = path.split('/')
    return p[1] if len(p) > 2 and p[0] == 'arch' else None


def is_def(text):
    t = text.rstrip()
    return bool(DEF_LINE.match(t)) and not t.endswith(';') and not t.startswith(('return', 'typedef', 'extern', 'static_assert'))


def found_outside_arch(rev, names, kconfig):
    """Names referenced outside arch/ (as NAME or CONFIG_NAME when kconfig)."""
    found, names = set(), sorted(names)
    for k in range(0, len(names), 150):
        alt = '|'.join(map(re.escape, names[k:k + 150]))
        pat = r'\b(CONFIG_)?(%s)\b' % alt if kconfig else r'\b(%s)\b' % alt
        for _, text in grep_lines(rev, pat, ':!arch/', ':!Documentation/', ':!tools/', opts=('-o', '-E')):
            found.add(text[7:] if text.startswith('CONFIG_') else text)
    return found


@lru_cache(maxsize=None)
def weak_names(rev):
    names = set()
    for _, text in grep_lines(rev, r'\b__weak\b', '*.c', ':!arch/', ':!tools/'):
        if text.rstrip().endswith(';') or text.lstrip().startswith(('*', '/')):
            continue
        m = re.search(r'([A-Za-z_]\w*)\s*\(', text.split('__weak', 1)[1] if '__weak' in text else text)
        if m and len(m.group(1)) >= 4:
            names.add(m.group(1))
    return names


def weak_union():
    """Every name that is __weak in non-arch .c at v4.15 or on an added __weak line since: a superset of weak_names(rev)
    for any rev in range, used only to skip the per-commit check for names that were never __weak."""
    names = set(weak_names('v4.15'))
    log = git('log', '--no-merges', '-p', '-U0', '--format=', '-G', '__weak', 'v4.15..' + END, '--', '*.c', ':!arch/', ':!tools/')
    for line in log.splitlines():
        if line.startswith('+') and not line.startswith('+++') and '__weak' in line:
            m = re.search(r'([A-Za-z_]\w*)\s*\(', line.split('__weak', 1)[1])
            if m:
                names.add(m.group(1))
    return names


@lru_cache(maxsize=None)
def common_guards(rev):
    out = set()
    for _, text in grep_lines(rev, r'#\s*ifndef\s+\w+|!\s*defined', 'include/'):
        for a, b in GUARD.findall(text):
            out.add(a or b)
    return out


def inventory(rev):
    """{kind:name: set(arches)} with the common-consumer filter of criteria.md."""
    prov = {}
    add = lambda key, path: prov.setdefault(key, set()).add(arch_of(path))
    for path, text in grep_lines(rev, r'^\s*select\s+%s' % K_PREFIX, 'arch/*Kconfig*'):
        m = K_LINE.match(text)
        if m and arch_of(path):
            add('K:' + m.group(1), path)
    for path, text in grep_lines(rev, r'^\s*#\s*define\s+%s' % M_PREFIX, 'arch/'):
        m = M_LINE.match(text)
        if m and arch_of(path):
            add('M:' + m.group(1), path)
    guards = common_guards(rev)
    for path, text in grep_lines(rev, r'^\s*#\s*define\s+[A-Za-z_]\w*\s+[A-Za-z_]\w*\s*$', 'arch/*.h'):
        m = S_LINE.match(text)
        if m and m.group(1) == m.group(2) and m.group(1) in guards and len(m.group(1)) >= 4 and arch_of(path):
            add('S:' + m.group(1), path)
    weak = sorted(weak_names(rev))
    for k in range(0, len(weak), 150):
        alt = '|'.join(map(re.escape, weak[k:k + 150]))
        for path, text in grep_lines(rev, r'^[A-Za-z_][^;(]*\b(%s)\s*\(' % alt, 'arch/*.c'):
            m = DEF_LINE.match(text)
            if m and m.group(1) in weak and is_def(text) and arch_of(path):
                add('W:' + m.group(1), path)
    for kind, kc in (('K', True), ('M', False)):
        names = {k[2:] for k in prov if k[0] == kind}
        used = found_outside_arch(rev, names, kc) if names else set()
        for n in names - used:
            prov.pop(kind + ':' + n)
    return prov


def gaps(inv, rule='main'):
    out = []
    for key, p in inv.items():
        if 'riscv' in p:
            continue
        if (rule == 'main' and {'x86', 'arm64'} <= p) or (rule == 'arm64' and 'arm64' in p) or \
           (rule == '3of4' and len(p & set(REFS)) >= 3):
            out.append(key)
    return sorted(out)


def provisions_stream():
    """[(commit, key)] for riscv commits in v4.15..END whose added arch/riscv lines provide an interface."""
    out, commit, path = [], None, None
    log = git('log', '--no-merges', '-p', '-U0', '--no-renames', '--format=COMMIT %H', 'v4.15..' + END, '--', 'arch/riscv')
    for line in log.splitlines():
        if line.startswith('COMMIT '):
            commit = line[7:]
            continue
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
            continue
        if not path or not line.startswith('+') or line.startswith('+++'):
            continue
        text = line[1:]
        m = K_LINE.match(text) if 'Kconfig' in path else None
        if m:
            out.append((commit, 'K:' + m.group(1)))
        m = M_LINE.match(text)
        if m:
            out.append((commit, 'M:' + m.group(1)))
        m = S_LINE.match(text)
        if m and m.group(1) == m.group(2) and len(m.group(1)) >= 4 and path.endswith('.h'):
            out.append((commit, 'S:' + m.group(1)))
        if path.endswith('.c') and is_def(text):
            out.append((commit, 'W?' + DEF_LINE.match(text).group(1)))
    return out


def provides(rev, key, arch):
    kind, name = key[0], key[2:]
    base = 'arch/%s/' % arch
    if kind == 'K':
        return any(K_LINE.match(t) and K_LINE.match(t).group(1) == name for _, t in grep_lines(rev, r'select\s+%s\b' % re.escape(name), base + '*Kconfig*'))
    if kind == 'M':
        return bool(grep_lines(rev, r'^\s*#\s*define\s+%s\b' % re.escape(name), base))
    if kind == 'S':
        return any(S_LINE.match(t) and S_LINE.match(t).group(1) == S_LINE.match(t).group(2) == name
                   for _, t in grep_lines(rev, r'^\s*#\s*define\s+%s\s+%s\s*$' % (re.escape(name), re.escape(name)), base + '*.h'))
    return any(is_def(t) and DEF_LINE.match(t).group(1) == name for _, t in grep_lines(rev, r'^[A-Za-z_][^;(]*\b%s\s*\(' % re.escape(name), base + '*.c'))


def consumed(rev, key):
    kind, name = key[0], key[2:]
    if kind == 'K':
        return bool(found_outside_arch(rev, {name}, True))
    if kind == 'M':
        return bool(found_outside_arch(rev, {name}, False))
    if kind == 'S':
        return name in common_guards(rev)
    return name in weak_names(rev)


def judge_provision(commit, key):
    """At commit^: is this a new riscv provision of a consumed interface, and was it a main-rule gap?"""
    parent = commit + '^'
    if key.startswith('W?'):
        key = 'W:' + key[2:]
    if provides(parent, key, 'riscv') or not consumed(parent, key):
        return None
    refs = {a for a in REFS if provides(parent, key, a)}
    return {'refs': sorted(refs), 'gap_main': {'x86', 'arm64'} <= refs, 'gap_arm64': 'arm64' in refs, 'gap_3of4': len(refs) >= 3}


def latest_lts_before(commit):
    best = None
    for t in LTS:
        if subprocess.run(['git', '-C', REPO, 'merge-base', '--is-ancestor', t, commit + '^']).returncode == 0:
            best = t
    return best


def main():
    target = HERE / 'stats.json'
    if target.exists():
        raise SystemExit('preserve')
    invs = {}
    for rev in LTS + [END]:
        invs[rev] = inventory(rev)
        print('inventory', rev, len(invs[rev]), 'gaps', len(gaps(invs[rev])), flush=True)
    gap_sets = {rev: {r: gaps(invs[rev], r) for r in ('main', 'arm64', '3of4')} for rev in invs}
    fixers = X.log_fixes()
    stream = sorted(set(provisions_stream()))
    print('provision lines', len(stream), flush=True)
    union = weak_union()
    stream = [(c, k) for c, k in stream if not k.startswith('W?') or k[2:] in union]
    print('after weak prefilter', len(stream), flush=True)

    def one(item):
        commit, key = item
        if key.startswith('W?') and key[2:] not in weak_names(commit + '^'):
            return None
        j = judge_provision(commit, key)
        if j is None:
            return None
        lts = latest_lts_before(commit)
        k = 'W:' + key[2:] if key.startswith('W?') else key
        return {'commit': commit, 'key': k, 'fix': commit in fixers, **j, 'lts_before': lts,
                'gap_at_lts': bool(lts) and k in set(gap_sets[lts]['main'])}

    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, r in enumerate(pool.map(one, stream), 1):
            if r:
                rows.append(r)
            if n % 200 == 0:
                print('progress', n, len(stream), flush=True)
    fixes = [r for r in rows if r['fix']]
    share = lambda rs, k: (sum(1 for r in rs if r[k]), len(rs))
    end_inv = invs[END]
    fate = {}
    for rev in LTS:
        f = {'filled': 0, 'still_gap': 0, 'gone': 0, 'filled_by_fix': 0}
        fixed_keys = {r['key'] for r in fixes}
        for key in gap_sets[rev]['main']:
            p = end_inv.get(key)
            if p is None or not {'x86', 'arm64'} <= p:
                f['gone'] += 1
            elif 'riscv' in p:
                f['filled'] += 1
                f['filled_by_fix'] += key in fixed_keys
            else:
                f['still_gap'] += 1
        fate[rev] = f
    sizes = [len(gap_sets[r]['main']) for r in LTS]
    filled = sum(fate[r]['filled'] for r in LTS) / max(1, sum(sizes))
    recall = share(fixes, 'gap_main')
    cases = json.loads((C_DIR / 'ccp_candgen_v2_20261030' / 'riscv_cases.json').read_text(encoding='utf-8'))['cases']
    case_rows = [{'target': c['target'], 'kind': c['kind'], 'provisions': [r for r in rows if r['commit'] == c['target']]} for c in cases]
    rec = recall[0] / recall[1] if recall[1] else 0
    decision = ('descriptive_only_truth_lt_15' if recall[1] < 15 else
                'useful_build_current_check' if rec >= 0.5 and statistics.median(sizes) <= 150 and filled >= 0.2 else
                'insufficient' if rec < 0.3 else 'between_analyse_misses')
    sample = random.Random(20261030).sample(gap_sets[END]['main'], min(20, len(gap_sets[END]['main'])))
    stats = {'end': END, 'inventory_size': {r: len(invs[r]) for r in invs},
             'gaps': {r: {k: len(v) for k, v in gap_sets[r].items()} for r in invs},
             'gaps_by_kind_main': {r: {kd: sum(1 for g in gap_sets[r]['main'] if g[0] == kd) for kd in 'KMSW'} for r in invs},
             'truth_fix_entries': len(fixes), 'truth_fix_commits': len({r['commit'] for r in fixes}),
             'recall_main': recall, 'recall_arm64': share(fixes, 'gap_arm64'), 'recall_3of4': share(fixes, 'gap_3of4'),
             'lead_gap_at_lts': share([r for r in fixes if r['gap_main']], 'gap_at_lts'),
             'all_provisions': {'entries': len(rows), 'gap_main': sum(r['gap_main'] for r in rows)},
             'lts_fate': fate, 'lts_gap_median': statistics.median(sizes), 'lts_filled_share': round(filled, 3),
             'riscv_cases_with_provisions': sum(1 for c in case_rows if c['provisions']),
             'decision': decision, 'kimi_calls': 0}
    (HERE / 'gaps.json').write_text(json.dumps({'gaps': gap_sets, 'end_inventory': {k: sorted(v) for k, v in end_inv.items()},
                                                'manual_sample': sample}, indent=1) + '\n')
    (HERE / 'provisions.json').write_text(json.dumps({'rows': rows, 'riscv_cases': case_rows}, indent=1) + '\n')
    target.write_text(json.dumps(stats, indent=1) + '\n')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
