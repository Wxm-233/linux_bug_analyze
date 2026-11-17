"""Direction 4, round 4 checks (criteria.md part 2). WSL; no model calls.
A: page-table hooks in include/linux/pgtable.h (#ifndef name / #ifndef __HAVE_ARCH_*, names starting pgd/p4d/pud/pmd/pte)
   that arm64 overrides and riscv does not.
B: same-named functions in arch/{arm64,riscv}/mm/*.c (not hugetlbpage.c) and arch/{arm64,riscv}/include/asm/pgtable*.h,
   body plus one level of same-file callees; walk steps W1-W6; flag = arm64 has, riscv lacks.
Runs at the parents of the mechanism cases and at the range end. Output: checks.json; prints a summary.
"""
from pathlib import Path
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(C_DIR / 'mech_riscv_hugetlb_20261030'))
from linux_bug_analyze.sibling_pairs import named_spans  # noqa: E402
import hugecheck as HC  # noqa: E402  (overrides)

REPO = '/root/repos/linux'
END = 'df2908090cda'
PREFIX = re.compile(r'^(pgd|p4d|pud|pmd|pte)')
MECH = ('folding', 'leaf_bad', 'read_concurrency')
STEPS = {
    'W1': r'\b(pgd|p4d|pud|pmd|pte)p_get\s*\(|\bREAD_ONCE\s*\(',
    'W2': r'_offset_lockless\s*\(',
    'W3': r'\b(pgd|p4d|pud|pmd)_leaf\s*\(',
    'W4': r'_(none|bad)\s*\(',
    'W5': r'\blocal_irq_(save|disable)\s*\(|\brcu_read_lock\s*\(',
    'W6': r'_present\s*\(',
}


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def hooks(rev):
    out = {}
    for m in re.finditer(r'^\s*#\s*ifndef\s+([A-Za-z_]\w*)', git('show', '%s:include/linux/pgtable.h' % rev), re.M):
        g = m.group(1)
        name = g[len('__HAVE_ARCH_'):].lower() if g.startswith('__HAVE_ARCH_') else g
        if PREFIX.match(name) and (g.startswith('__HAVE_ARCH_') or re.fullmatch(r'[a-z_][a-z0-9_]*', g)):
            out[name] = g
    return out


def check_a(rev):
    out = []
    for name, guard in sorted(hooks(rev).items()):
        a, r = HC.overrides(rev, 'arm64', name, guard), HC.overrides(rev, 'riscv', name, guard)
        if a and not r:
            out.append({'hook': name, 'guard': guard})
    return out


def functions(rev, arch):
    """{name: expanded text} for the arch's mm .c files (not hugetlbpage.c) and pgtable*.h headers."""
    paths = [p for p in git('ls-tree', '-r', '--name-only', rev, 'arch/%s/mm' % arch, 'arch/%s/include/asm' % arch).splitlines()
             if (p.startswith('arch/%s/mm/' % arch) and p.endswith('.c') and not p.endswith('hugetlbpage.c'))
             or re.search(r'/include/asm/pgtable[^/]*\.h$', p)]
    out = {}
    for p in paths:
        text = git('show', '%s:%s' % (rev, p))
        lines = text.splitlines()
        bodies = {}
        for s, e, name in named_spans(text):
            bodies[name] = bodies.get(name, '') + '\n' + '\n'.join(lines[s - 1:e])
        for name, body in bodies.items():
            called = {c for c in re.findall(r'\b([A-Za-z_]\w*)\s*\(', body)} & set(bodies) - {name}
            out.setdefault(name, {'paths': [], 'text': ''})
            out[name]['paths'].append(p)
            out[name]['text'] += body + '\n' + '\n'.join(bodies[c] for c in sorted(called))
    return out


def steps(text):
    return {k for k, pat in STEPS.items() if re.search(pat, text)}


def check_b(rev):
    a, r = functions(rev, 'arm64'), functions(rev, 'riscv')
    out = []
    for name in sorted(set(a) & set(r)):
        sa, sr = steps(a[name]['text']), steps(r[name]['text'])
        for s in sorted(sa - sr):
            out.append({'func': name, 'missing': s, 'arm64': sorted(sa), 'riscv': sorted(sr), 'riscv_paths': r[name]['paths']})
    return out


def main():
    target = HERE / 'checks.json'
    if target.exists():
        raise SystemExit('preserve')
    cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))['cases']
    alias = {'remove_pud_mapping': ['remove_pud_mapping', 'remove_p4d_mapping'],
             'set_direct_map_invalid_noflush': ['set_direct_map_invalid_noflush', 'set_direct_map_default_noflush']}
    retro = []
    for c in cases:
        if c['class'] not in MECH:
            continue
        parent = c['commit'] + '^'
        names = alias.get(c['hook'], [c['hook']])
        a, b = check_a(parent), check_b(parent)
        hit_a = [x for x in a if x['hook'] in names]
        hit_b = [x for x in b if x['func'] in names]
        retro.append({**c, 'flagged': bool(hit_a or hit_b), 'hit_a': hit_a, 'hit_b': hit_b, 'flags_a': len(a), 'flags_b': len(b),
                      'flags_total': len(a) + len(b)})
        print('retro', c['commit'], c['hook'], bool(hit_a or hit_b), len(a), len(b), flush=True)
    end_a, end_b = check_a(END), check_b(END)
    summary = {'cases': len(cases), 'mechanism_cases': len(retro), 'retro_flagged': sum(r['flagged'] for r in retro),
               'parent_flags_max': max((r['flags_total'] for r in retro), default=0),
               'end_flags_a': len(end_a), 'end_flags_b': len(end_b)}
    target.write_text(json.dumps({'summary': summary, 'retro': retro, 'end_a': end_a, 'end_b': end_b}, indent=1) + '\n')
    print(json.dumps(summary))
    print('END A', [x['hook'] for x in end_a])
    print('END B', [(x['func'], x['missing']) for x in end_b])


if __name__ == '__main__':
    main()
