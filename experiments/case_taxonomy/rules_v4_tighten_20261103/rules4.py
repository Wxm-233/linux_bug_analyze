"""Version-4 rules CTX, R7 and R10 (rules_v4_tighten_20261103/criteria.md: version 3 plus T1, T2, T4) on one
snapshot. WSL; no model calls; labels are not read.
Usage: python3 rules2.py SNAPSHOT OUT.json. Every flag has rule, path, name, start, end, reason, issue (I3 key).
"""
from pathlib import Path
import ast
import importlib.util
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
import modules as M  # noqa: E402
from modules import REF, ARCH_WORDS, call_names, function  # noqa: E402

spec = importlib.util.spec_from_file_location('mr', HERE.parent / 'mech_rules_riscv_20261103' / 'rules.py')
MR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MR)  # R7 matcher, AUX list, params()
SNAP = None
R7_FILES = re.compile(r'arch/riscv/kvm/.*\.c$|arch/riscv/kernel/(ptrace|signal|sys_riscv|vector|compat_\w+|process)\.c$')
CONST_ARG = re.compile(r'\s*([A-Z][A-Z0-9_]*|0x[0-9a-fA-F]+|\d+)\s*')


def git(*a):
    return M.git(*a)


# ------------------------------------------------------------------ R7 (I5)
def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    return out + [cur]


def internal_constant(name, text, var):
    """True when var is a parameter of name and every call site in arch/riscv passes a constant there (I5)."""
    head = text.split('{', 1)[0]
    m = re.search(r'\((.*)\)\s*$', head.strip(), re.S)
    if not m:
        return False
    plist = [MR.IDENT.findall(p.split('[')[0]) for p in split_args(m.group(1))]
    pos = next((i for i, ids in enumerate(plist) if ids and ids[-1] == var), None)
    if pos is None:
        return False
    sites = 0
    for h in git('grep', '-h', '-E', r'(^|[^A-Za-z0-9_])' + name + r'[[:space:]]*\(', SNAP, '--', 'arch/riscv').splitlines():
        for mm in re.finditer(r'(?<![A-Za-z0-9_])' + name + r'\s*\(([^;]*)\)\s*;', h):
            args = split_args(mm.group(1))
            if any(re.fullmatch(r'\s*(const\s+)?(struct\s+|unsigned\s+|enum\s+)?\w+[\s*]+\w+\s*', a) for a in args):
                continue  # P4: a prototype, not a call
            if len(args) > pos:
                sites += 1
                if not CONST_ARG.fullmatch(args[pos]):
                    return False
    return sites > 0


def r7_function(path, s, e, name, text):
    """MR.r7_function with P3: derived variables are parameters and locals assigned (transitively) from them."""
    derived = set(MR.params(text))
    assigns = [m for l in text.splitlines() for m in [re.search(r'\b([A-Za-z_]\w*)\s*=\s*([^;=][^;]*);', l)] if m]
    changed = True
    while changed:
        changed = False
        for m in assigns:
            if m.group(1) not in derived and any(re.search(r'\b' + re.escape(v) + r'\b',
                                                           re.sub(r'\b' + re.escape(v) + r'\s*(->|\.)\s*\w+', '', m.group(2)))
                                                 for v in derived):  # T1: a field read through v is not input
                derived.add(m.group(1))
                changed = True
    lines, found = text.splitlines(), []
    for k, l in enumerate(lines):
        for m in re.finditer(r'\b[A-Za-z_][\w>.\-]*\s*\[\s*([A-Za-z_]\w*)\s*(?:-\s*\w+\s*)?\]', l):
            v = m.group(1)
            if v not in derived or v.isupper() or re.search(r'\bfor\s*\([^;]*\b' + v + r'\b\s*=', text):
                continue
            if re.search(r'array_index_nospec\s*\(\s*' + re.escape(v) + r'\b', text):
                continue
            cmp = re.compile(r'\b' + re.escape(v) + r'\s*(>=|>|<=|<)(?!<)|(>=|>|<=|<)\s*' + re.escape(v) + r'\b')
            for j in range(k):
                if re.search(r'\bif\s*\(', lines[j]) and cmp.search(lines[j]) and \
                        any(re.search(r'\b(return|goto)\b', x) for x in lines[j:j + 3]):
                    found.append((s + k, v, s + j))
                    break
    return found


def r7():
    out = []
    for p in [p for p in M.files(SNAP, 'arch/riscv', ('.c',)) if R7_FILES.match(p)]:
        for s, e, n, t in M.funcs(SNAP, p):
            hits = [h for h in r7_function(p, s, e, n, t) if not internal_constant(n, t, h[1])]
            if hits:
                out.append({'rule': 'R7', 'path': p, 'name': n, 'start': s, 'end': e,
                            'reason': '; '.join(f'line {a}: [{v}] after bound check at line {c}, no array_index_nospec'
                                                for a, v, c in hits[:3]),
                            'issue': f'R7|{p}:{n}'})
    return out


# ------------------------------------------------------------------ R10 (I4)
def is_stub(text):
    body = re.sub(r'/\*.*?\*/|//[^\n]*', '', text.split('{', 1)[1] if '{' in text else '', flags=re.S)
    body = body.rsplit('}', 1)[0]
    stmts = [x.strip() for x in body.split(';') if x.strip()]
    rets = re.findall(r'\breturn\b([^;]*);', body)
    const = all(re.fullmatch(r'\s*(-?\w*E[A-Z]+|-?\d+|NULL|0|false|true|)\s*', r) or
                re.fullmatch(r'\s*-\s*[A-Z]+\s*', r) for r in rets)
    return len(stmts) <= 2 and const


_KCONFIG = None


def riscv_kconfig():
    global _KCONFIG
    if _KCONFIG is None:
        _KCONFIG = ''.join(git('show', f'{SNAP}:{p}') for p in
                           git('ls-tree', '-r', '--name-only', SNAP, 'arch/riscv').splitlines() if 'Kconfig' in p)
    return _KCONFIG


def config_gated_off(x):
    """X has an empty fallback under the #else of a CONFIG_Y test in include/, and riscv's Kconfig never names Y."""
    for h in git('grep', '-n', '-E', r'(static inline .*[^A-Za-z0-9_]' + x + r'[[:space:]]*\(.*\)[[:space:]]*\{[[:space:]]*\}'
                 r'|static inline .*[^A-Za-z0-9_]' + x + r'[[:space:]]*\(|#[[:space:]]*define[[:space:]]+' + x + r'[[:space:]]*\()',
                 SNAP, '--', 'include/').splitlines():
        p = h.split(':', 3)
        if len(p) < 4:
            continue
        lines = git('show', f'{SNAP}:{p[1]}').splitlines()
        k = int(p[2]) - 1
        tail = ' '.join(lines[k:k + 3])
        if not re.search(x + r'\s*\([^)]*\)\s*(\{\s*\}|\{\s*return[^;]*;\s*\}|do\s*\{\s*\}\s*while\s*\(0\)|$)', tail):
            continue
        depth, seen_else = 0, False
        for j in range(k - 1, -1, -1):
            l = lines[j].strip()
            if re.match(r'#\s*endif', l):
                depth += 1
            elif re.match(r'#\s*(else|elif)', l) and depth == 0:
                seen_else = True
            elif re.match(r'#\s*if', l):
                if depth == 0:
                    m = re.search(r'CONFIG_(\w+)', l)
                    if m and seen_else and m.group(1) not in riscv_kconfig():
                        return True
                    break
                depth -= 1
    return False


def callee_text(name):
    defs = M.defs_in(SNAP, [name], ('arch/riscv/*.c', 'arch/riscv/*.h', 'kernel/*.c', 'mm/*.c', 'lib/*.c',
                                    'include/linux/*.h', 'include/asm-generic/*.h'))
    for p in sorted(defs.get(name, []), key=lambda p: not p.startswith('arch/riscv')):
        f = function(SNAP, p, name)
        if f:
            return f['text']
    return None


def reached(rv, x, depth=2):
    """P5: x is called by a function that rv's implementation calls, within depth levels."""
    if not rv:
        return False
    frontier, seen = [rv['text']], set()
    for _ in range(depth):
        nxt = []
        for t in frontier:
            for c in call_names(t):
                if c in seen:
                    continue
                seen.add(c)
                ct = callee_text(c)
                if ct is None:
                    continue
                if x in call_names(ct):
                    return True
                nxt.append(ct)
        frontier = nxt
    return False


def r10():
    out = []
    for f in MR.r10():
        rv = function(SNAP, f['path'], f['name'])
        if rv and is_stub(rv['text']):
            continue
        missing = re.search(r'call (\[.*\]), riscv', f['reason'])
        names = ast.literal_eval(missing.group(1)) if missing else []  # list literal written by MR.r10
        names = [x for x in names if not config_gated_off(x) and not reached(rv, x)]  # P5
        if names:
            out.append({**f, 'reason': f'all three references call {names}, riscv does not',
                        'issue': f'R10|{f["path"]}:{f["name"]}'})
    return out


# ------------------------------------------------------------------ CTX v2
def ctx():
    spec2 = importlib.util.spec_from_file_location('ctx4', HERE / 'ctx4.py')
    C = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(C)
    C.SNAP = SNAP
    idx, _ = C.build_index()
    C.INDEX.update(idx)
    flags, _ = C.run()
    out = []
    for f in C.dedupe(flags):
        last = f['chain'][-1][1] if f['chain'] else f['function']
        out.append({'rule': 'CTX', 'path': f['path'], 'name': f['function'], 'start': f['start'], 'end': f['end'],
                    'reason': f'{f["kind"]} {f["source"]}: line {f["line"]} {f["call"]} -> {f["sink"]}',
                    'chain': f['chain'], 'kind': f['kind'], 'source': f['source'],
                    'issue': f'CTX|{f["kind"]}|{last}|{f["sink"]}'})  # I3
    return out


def main():
    global SNAP
    SNAP, out_name = sys.argv[1], sys.argv[2]
    MR.SNAP = SNAP
    target = HERE / out_name
    if target.exists():
        raise SystemExit('preserve')
    t0, flags, stats = time.time(), [], {'snapshot': SNAP}
    for name, fn in (('CTX', ctx), ('R7', r7), ('R10', r10)):
        t = time.time()
        got = fn()
        flags += got
        stats[name] = {'flags': len(got), 'issues': len({f['issue'] for f in got}), 'seconds': round(time.time() - t)}
    stats['seconds'] = round(time.time() - t0)
    target.write_text(json.dumps({'stats': stats, 'flags': flags}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
