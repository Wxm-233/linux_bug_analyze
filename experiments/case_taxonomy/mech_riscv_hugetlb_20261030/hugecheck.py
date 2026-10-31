"""Direction 4 checks (criteria.md). WSL; no model calls.
A: hugetlb hooks common code lets architectures override (#ifndef __HAVE_ARCH_X / #ifndef name in include/linux/hugetlb.h and
   include/asm-generic/hugetlb.h; __weak definitions in mm/hugetlb.c) that arm64 overrides and riscv does not.
B: *get_and_clear* page-table functions whose implementation effective on riscv (riscv's own, else the common default)
   has no atomic exchange; arm64 and x86 effective implementations listed for reference.
Runs at each case's parent (retrospective) and at the range end. Output: checks.json; prints a summary.
"""
from pathlib import Path
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
END = 'df2908090cda'
HOOK_FILES = ('include/linux/hugetlb.h', 'include/asm-generic/hugetlb.h')
WEAK_FILES = ('mm/hugetlb.c',)
GENERIC = ('include/linux/pgtable.h', 'include/asm-generic/', 'include/linux/hugetlb.h', 'mm/')
ATOMIC = re.compile(r'\b(xchg|__xchg|atomic_long_xchg|atomic_xchg|atomic64_xchg|amoswap\w*|cmpxchg|try_cmpxchg|xchg_relaxed)\b')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def show(rev, path):
    return git('show', '%s:%s' % (rev, path))


def hooks(rev):
    """{hook name: guard} overridable hugetlb hooks at rev."""
    out = {}
    for f in HOOK_FILES:
        for m in re.finditer(r'^\s*#\s*ifndef\s+([A-Za-z_]\w*)', show(rev, f), re.M):
            g = m.group(1)
            if g.startswith('__HAVE_ARCH_'):
                out[g[len('__HAVE_ARCH_'):].lower()] = g
            elif re.fullmatch(r'[a-z_][a-z0-9_]*', g):
                out[g] = g
    for f in WEAK_FILES:
        for m in re.finditer(r'^[^\n;]*\b__weak\b[^\n(;]*?\b([A-Za-z_]\w*)\s*\(', show(rev, f), re.M):
            out.setdefault(m.group(1), '__weak')
    return out


def overrides(rev, arch, name, guard):
    base = 'arch/%s/' % arch
    if guard.startswith('__HAVE_ARCH_'):
        if git('grep', '-l', '-E', r'^\s*#\s*define\s+%s\b' % guard, rev, '--', base):
            return True
    if git('grep', '-l', '-E', r'^\s*#\s*define\s+%s(\s+%s\s*$|\()' % (name, name), rev, '--', base):
        return True
    for line in git('grep', '-h', '-E', r'^[A-Za-z_][^;(]*\b%s\s*\(' % name, rev, '--', base + '*.c', base + '*.h').splitlines():
        if not line.rstrip().endswith(';') and not line.startswith(('extern', 'return')):
            return True
    return False


def body_after(text, i):
    """Text of the {...} block starting at or after index i, or None."""
    j = text.find('{', i)
    if j < 0:
        return None
    depth = 0
    for k in range(j, len(text)):
        depth += text[k] == '{'
        depth -= text[k] == '}'
        if depth == 0:
            return text[j:k + 1]
    return None


def definition(rev, name, paths):
    """(path, body) of the first function definition or function-like macro of name under paths."""
    for path in git('grep', '-l', '-w', name, rev, '--', *paths).splitlines():
        path = path.split(':', 1)[1]
        text = show(rev, path)
        m = re.search(r'^\s*#\s*define\s+%s\((.*(?:\\\n.*)*)' % re.escape(name), text, re.M)
        if m:
            return path, m.group(0)
        for m in re.finditer(r'\b%s\s*\(' % re.escape(name), text):
            depth, k = 0, m.end() - 1
            while k < len(text):
                depth += text[k] == '('
                depth -= text[k] == ')'
                if depth == 0:
                    break
                k += 1
            rest = text[k + 1:k + 200].lstrip()
            line_start = text.rfind('\n', 0, m.start()) + 1
            prefix = text[line_start:m.start()]
            if rest.startswith('{') and not re.search(r'\breturn\b|=', prefix):
                return path, body_after(text, k + 1)
    return None, None


def get_and_clear_names(rev):
    names = set()
    for line in git('grep', '-h', '-o', '-E', r'\b\w*get_and_clear\w*\s*\(', rev, '--', 'arch/riscv/', 'arch/arm64/', 'arch/x86/',
                    'include/linux/pgtable.h', 'include/asm-generic/', 'include/linux/hugetlb.h').splitlines():
        n = line.split('(')[0].strip()
        if re.fullmatch(r'(ptep|pmdp|pudp|p4dp|huge_ptep)\w*get_and_clear\w*', n):
            names.add(n)
    return sorted(names)


def effective(rev, arch, name):
    path, body = definition(rev, name, ['arch/%s/' % arch])
    src = 'arch'
    if body is None:
        path, body = definition(rev, name, list(GENERIC))
        src = 'generic' if body is not None else None
    return {'source': src, 'path': path, 'atomic': bool(body and ATOMIC.search(body)), 'found': body is not None}


def check_a(rev):
    out = []
    for name, guard in sorted(hooks(rev).items()):
        a, r = overrides(rev, 'arm64', name, guard), overrides(rev, 'riscv', name, guard)
        out.append({'hook': name, 'guard': guard, 'arm64': a, 'riscv': r, 'flag': a and not r})
    return out


def check_b(rev):
    out = []
    for name in get_and_clear_names(rev):
        rv = effective(rev, 'riscv', name)
        if not rv['found']:
            continue
        out.append({'func': name, 'riscv': rv, 'arm64': effective(rev, 'arm64', name), 'x86': effective(rev, 'x86', name),
                    'flag': not rv['atomic']})
    return out


def main():
    target = HERE / 'checks.json'
    if target.exists():
        raise SystemExit('preserve')
    cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))['cases']
    retro = []
    for c in cases:
        if c['class'] not in ('multi_entry_default', 'atomicity'):
            continue
        parent = c['commit'] + '^'
        if c['class'] == 'multi_entry_default':
            a = check_a(parent)
            hit = [x for x in a if x['hook'] == c['hook']]
            retro.append({**c, 'check': 'A', 'hook_listed': bool(hit), 'flagged': bool(hit and hit[0]['flag']), 'detail': hit,
                          'flags_at_parent': len([x for x in a if x['flag']])})
        else:
            b = check_b(parent)
            hit = [x for x in b if x['func'] == c['hook']]
            retro.append({**c, 'check': 'B', 'func_listed': bool(hit), 'flagged': bool(hit and hit[0]['flag']), 'detail': hit,
                          'flags_at_parent': len([x for x in b if x['flag']])})
        print('retro', c['commit'], c['hook'], retro[-1]['flagged'], flush=True)
    also = [{**c, 'flagged_by_A': any(x['hook'] == c['hook'] and x['flag'] for x in check_a(c['commit'] + '^'))}
            for c in cases if c['class'] in ('other', 'contract_change') and c['hook']]
    end_a, end_b = check_a(END), check_b(END)
    summary = {'cases': len(cases), 'mechanism_cases': len(retro), 'retro_flagged': sum(r['flagged'] for r in retro),
               'end_flags_A': [x['hook'] for x in end_a if x['flag']], 'end_flags_B': [x['func'] for x in end_b if x['flag']],
               'end_hooks_total': len(end_a), 'end_b_total': len(end_b)}
    target.write_text(json.dumps({'summary': summary, 'retro': retro, 'other_cases_A': also, 'end_A': end_a, 'end_B': end_b}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
