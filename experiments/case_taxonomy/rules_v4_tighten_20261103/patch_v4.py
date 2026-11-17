"""Apply T1, T2, T4 (rules_v4_tighten_20261103/criteria.md) to the copies ctx4.py and rules4.py."""
import sys
from pathlib import Path

D = Path(sys.argv[1])


def patch(name, pairs):
    p = D / name
    s = p.read_text(encoding='utf-8')
    for a, b in pairs:
        assert s.count(a) == 1, (name, a[:70])
        s = s.replace(a, b)
    assert not any(ch in s for ch in '\x08\x0c'), 'control character'
    p.write_text(s, encoding='utf-8', newline='\n')


patch('ctx4.py', [
    ("cross calls), version 3 adds P1 (rules_v3_precision_20261103/criteria.md):",
     "cross calls), version 3 adds P1 (rules_v3_precision_20261103/criteria.md) and version 4 adds T2 and T4\n"
     "(rules_v4_tighten_20261103/criteria.md):"),
    # T4 in check_region
    ("""            s = (chain[-1][4], chain[-1][3])
        flags.append({'kind': s[0], 'source': source, 'via': via, 'path': owner['path'], 'function': owner['name'],""",
     """            s = (chain[-1][4], chain[-1][3])
            if shared_common_path(owner, source, c.name, chain):  # T4
                continue
        flags.append({'kind': s[0], 'source': source, 'via': via, 'path': owner['path'], 'function': owner['name'],"""),
    ("""def check_region(owner, cs, hard, source, via, flags):""",
     """@lru_cache(maxsize=None)
def ref_functions(name):
    \"\"\"Definitions of name in the reference architectures at SNAP: [(path, text)].\"\"\"
    out = []
    for h in CK.git('grep', '-n', '-E', r'^[A-Za-z_].*[^A-Za-z0-9_]' + name + r'[[:space:]]*\\(', SNAP, '--',
                    *[f'arch/{a}' for a in REF]).splitlines():
        p = h.split(':', 3)
        if len(p) == 4 and not p[3].rstrip().endswith(';'):
            for s, e, n, t in CK.functions(SNAP, p[1]):
                if n == name and s - 8 <= int(p[2]) <= e:
                    out.append((p[1], t))
                    break
    return tuple(out)


def shared_common_path(owner, source, first, chain):
    \"\"\"T4: the violation happens in common code that a reference architecture's same-named function F also enters
    through the same common function G, and the atomic context is not F's own region.\"\"\"
    fns = [(owner['path'], owner['name'])] + [(x[0], x[1]) for x in chain]
    k = next((i for i, (p, _) in enumerate(fns) if not p.startswith(RISCV)), None)
    if k is None or k == 0:
        return False
    f_path, f_name = fns[k - 1]
    g_name = fns[k][1]
    if k - 1 == 0 and source.startswith('A'):
        return False
    return any(g_name in {c.name for c in analyze(t)} for _, t in ref_functions(f_name))


def check_region(owner, cs, hard, source, via, flags):"""),
    # T2 in N2
    ("""            if t and not re.search(r'(^|\\W)(noinstr|__cpuidle|__always_inline|inline)(\\W|$)', t['head']):""",
     """            if t and not re.search(r'(^|\\W)(noinstr|__cpuidle|__always_inline|inline)(\\W|$)', t['head']) \\
                    and ref_wraps(d['name'], c.name):  # T2"""),
    ("""@lru_cache(maxsize=None)
def ref_noinstr(name):""",
     """def ref_wraps(fname, callee):
    \"\"\"T2: some reference architecture's fname calls callee inside instrumentation_begin/end.\"\"\"
    for _, t in ref_functions(fname):
        cs = analyze(t)
        ins = inside(cs, lambda n: instr_effect(n) == INSTR_BEGIN, lambda n: instr_effect(n) == INSTR_END)
        if any(c.name == callee for c in ins):
            return True
    return False


@lru_cache(maxsize=None)
def ref_noinstr(name):"""),
])

patch('rules4.py', [
    ('"""Version-3 rules CTX, R7 and R10 (rules_v3_precision_20261103/criteria.md: version 2 plus P1, P3, P4, P5) on one',
     '"""Version-4 rules CTX, R7 and R10 (rules_v4_tighten_20261103/criteria.md: version 3 plus T1, T2, T4) on one'),
    ("spec2 = importlib.util.spec_from_file_location('ctx3', HERE / 'ctx3.py')",
     "spec2 = importlib.util.spec_from_file_location('ctx4', HERE / 'ctx4.py')"),
    ("""            if m.group(1) not in derived and any(re.search(r'\\b' + re.escape(v) + r'\\b', m.group(2)) for v in derived):""",
     """            if m.group(1) not in derived and any(re.search(r'\\b' + re.escape(v) + r'\\b',
                                                           re.sub(r'\\b' + re.escape(v) + r'\\s*(->|\\.)\\s*\\w+', '', m.group(2)))
                                                 for v in derived):  # T1: a field read through v is not input"""),
])
print('patched')
