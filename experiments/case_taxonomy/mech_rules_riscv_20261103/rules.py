"""Rules R1, R7, R8, R10 and the frozen CTX checker on one snapshot (criteria.md section 2). WSL; no model calls;
labels are not read. Usage: python3 rules.py OUT.json [RULE ...]  (default: all). Every flag has rule, path,
start, end (the flagged location at the snapshot) and a reason.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
import modules as M  # noqa: E402
from modules import REF, ARCH_WORDS, call_names, function  # noqa: E402

SNAP = 'v6.6'
SINCE = '2020-10-29'  # three years before the snapshot (R8)
IDENT = re.compile(r'[A-Za-z_]\w*')
KEYWORDS = set('if else for while do return switch case break continue goto sizeof struct union enum static const '
               'void int long short char unsigned signed bool true false NULL inline extern volatile default'.split())


def git(*a):
    return M.git(*a)


# ------------------------------------------------------------------ R1
def default_location(path, name):
    f = function(SNAP, path, name)
    if f:
        return f['start'], f['end']
    text = git('show', f'{SNAP}:{path}').splitlines()
    k = next((i for i, l in enumerate(text, 1) if re.match(r'#\s*ifndef\s+' + name + r'\s*$', l)), 1)
    e = next((i for i, l in enumerate(text[k:], k + 1) if l.startswith('#endif')), k + 20)
    return k, e


def r1():
    defaults = M.m1_defaults(SNAP)
    names = [n for n, _, _ in defaults]
    rv = M.defs_in(SNAP, names, ('arch/riscv/*.c', 'arch/riscv/*.h', 'drivers/acpi/riscv/*.c'), macros=True)
    per = {a: M.defs_in(SNAP, names, (f'arch/{a}/*.c', f'arch/{a}/*.h', f'drivers/acpi/{a}/*.c'), macros=True)
           for a in REF}
    out = []
    for n, p, kind in defaults:
        if p == 'include/asm-generic/percpu.h':  # amendment 1a
            continue
        if n not in rv and all(n in per[a] for a in REF):
            s, e = default_location(p, n)
            out.append({'rule': 'R1', 'path': p, 'name': n, 'start': s, 'end': e,
                        'reason': f'{kind} default overridden by arm64, x86 and loongarch, not by riscv',
                        'refs': {a: sorted(per[a][n])[:2] for a in REF}})
    return out


# ------------------------------------------------------------------ R7
def params(text):
    head = text.split('{', 1)[0]
    m = re.search(r'\((.*)\)\s*$', head.strip(), re.S)
    if not m:
        return set()
    out = set()
    for piece in m.group(1).split(','):
        ids = IDENT.findall(piece.split('[')[0])
        if ids:
            out.add(ids[-1])
    return out


def r7_function(path, s, e, name, text):
    lines = text.splitlines()
    ps = params(text)
    derived = set(ps)
    for l in lines:
        m = re.search(r'\b([A-Za-z_]\w*)\s*=\s*([^;=][^;]*);', l)
        if m and (any(re.search(r'\b' + re.escape(p) + r'\b', m.group(2)) for p in ps) or '->' in m.group(2)):
            derived.add(m.group(1))
    found = []
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
    paths = [p for p in M.files(SNAP, 'arch/riscv', ('.c',)) if p.startswith(('arch/riscv/kvm/', 'arch/riscv/kernel/'))]
    for p in paths:
        for s, e, n, t in M.funcs(SNAP, p):
            hits = r7_function(p, s, e, n, t)
            if hits:
                out.append({'rule': 'R7', 'path': p, 'name': n, 'start': s, 'end': e,
                            'reason': '; '.join(f'line {a}: [{v}] after bound check at line {c}, no array_index_nospec'
                                                for a, v, c in hits[:3])})
    return out


# ------------------------------------------------------------------ R8
def norm(l):
    return re.sub(r'\s+', '', l)


def ids(lines):
    return {x for l in lines for x in IDENT.findall(re.sub(r'/\*.*?\*/|//.*', '', l))} - KEYWORDS


def r8():
    rv = M.riscv_defs(SNAP, ('.c', '.h'))
    log = git('log', '--format=@@C %H', '-U0', '--grep=Fixes:', f'--since={SINCE}', SNAP, '--',
              *[f'arch/{a}' for a in REF])
    hunks, sha, path, cur = [], None, None, None
    for l in log.splitlines():
        if l.startswith('@@C '):
            sha = l[4:]
        elif l.startswith('+++ '):
            path = l[6:] if l.startswith('+++ b/') else None
        elif l.startswith('@@ '):
            m = re.match(r'@@ [^@]* @@(.*)', l)
            fn = re.findall(r'([A-Za-z_]\w*)\s*\(', m.group(1)) if m else []
            cur = {'sha': sha, 'path': path, 'name': fn[0] if fn else None, 'minus': [], 'plus': []}
            hunks.append(cur)
        elif cur is not None and l.startswith('-') and not l.startswith('---'):
            cur['minus'].append(l[1:])
        elif cur is not None and l.startswith('+') and not l.startswith('+++'):
            cur['plus'].append(l[1:])
    out, seen = [], set()

    def one(h):
        if not h['name'] or h['name'] not in rv or not h['path'] or not h['minus']:
            return None
        rp = sorted(rv[h['name']], key=lambda p: not p.endswith('.c'))[0]
        f = function(SNAP, rp, h['name'])
        if not f:
            return None
        rv_lines = {norm(x) for x in f['text'].splitlines()}
        ref_now = {norm(x) for x in git('show', f'{SNAP}:{h["path"]}').splitlines()}
        new_ids = ids(h['plus']) - ids(f['text'].splitlines())
        if not new_ids:
            return None
        for m in h['minus']:
            n = norm(m)
            if len(ids([m])) >= 3 and n in rv_lines and n not in ref_now and not m.strip().startswith(('/*', '*', '//')):
                return {'rule': 'R8', 'path': rp, 'name': h['name'], 'start': f['start'], 'end': f['end'],
                        'reason': f'{h["sha"][:12]} in {h["path"]} removed "{m.strip()[:100]}", still in riscv; '
                                  f'added {sorted(new_ids)[:6]}', 'ref_fix': h['sha'][:12]}
        return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        for x in pool.map(one, hunks):
            if x and (x['path'], x['name'], x['ref_fix']) not in seen:
                seen.add((x['path'], x['name'], x['ref_fix']))
                out.append(x)
    return out, len(hunks)


# ------------------------------------------------------------------ R10
AUX = re.compile(r'pr_\w+|printk\w*|seq_printf|dev_\w+|kmalloc\w*|kzalloc|kcalloc|kfree|kvfree|vfree|\w+_val|\w*for_each\w*')  # 1b

def r10():
    rv = M.riscv_defs(SNAP)
    names = [n for n in rv if n not in M.GENERIC and not n.startswith('riscv')]
    per_arch = {a: M.defs_in(SNAP, names, (f'arch/{a}/*.c', f'arch/{a}/*.h')) for a in REF}
    all3 = [n for n in names if all(n in per_arch[a] for a in REF)]
    common = M.called_in_common(SNAP, all3)
    out = []
    for n in sorted(set(all3) & common):
        rv_impl = next((function(SNAP, p, n) for p in sorted(rv[n], key=lambda p: not p.endswith('.c'))
                        if function(SNAP, p, n)), None)
        if not rv_impl:
            continue
        impls = {}
        for a in REF:
            for p in sorted(per_arch[a].get(n, []), key=lambda p: not p.endswith('.c')):
                f = function(SNAP, p, n)
                if f:
                    impls[a] = f
                    break
        if len(impls) < 3:
            continue
        rv_calls = call_names(rv_impl['text'])
        sets = [call_names(f['text']) - rv_calls for f in impls.values()]
        missing = sorted(c for c in set.intersection(*sets) if not ARCH_WORDS.search(c) and c != n
                         and not AUX.fullmatch(c))
        if missing:
            common_defs = M.defs_in(SNAP, missing, ('*.c', '*.h', ':(exclude)arch', ':(exclude)tools'), macros=True)
            missing = [c for c in missing if c in common_defs]
        if missing:
            out.append({'rule': 'R10', 'path': rv_impl['path'], 'name': n, 'start': rv_impl['start'],
                        'end': rv_impl['end'], 'reason': f'all three references call {missing[:8]}, riscv does not',
                        'refs': {a: f['path'] for a, f in impls.items()}})
    return out


# ------------------------------------------------------------------ CTX (frozen checker, snapshot overridden)
def ctx():
    spec = importlib.util.spec_from_file_location('ctxcheck', HERE.parent / 'ctx_rules_riscv_20261103' / 'ctxcheck.py')
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
    C.SNAP = SNAP
    idx, _ = C.build_index()
    C.INDEX.update(idx)
    flags, stats = C.run()
    out = []
    for f in C.dedupe(flags):
        out.append({'rule': 'CTX', 'path': f['path'], 'name': f['function'], 'start': f['start'], 'end': f['end'],
                    'reason': f'{f["kind"]} {f["source"]}: line {f["line"]} {f["call"]} -> {f["sink"]}',
                    'chain': f['chain'], 'kind': f['kind'], 'source': f['source']})
    return out


def main():
    out_name, rules = sys.argv[1], sys.argv[2:] or ['R1', 'R7', 'R8', 'R10', 'CTX']
    target = HERE / out_name
    if target.exists():
        raise SystemExit('preserve')
    t0, flags, stats = time.time(), [], {'snapshot': SNAP}
    for r in rules:
        t = time.time()
        if r == 'R8':
            got, n = r8()
            stats['r8_hunks'] = n
        else:
            got = {'R1': r1, 'R7': r7, 'R10': r10, 'CTX': ctx}[r]()
        flags += got
        stats[r] = {'flags': len(got), 'seconds': round(time.time() - t)}
    stats['seconds'] = round(time.time() - t0)
    target.write_text(json.dumps({'stats': stats, 'flags': flags}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
