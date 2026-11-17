"""Patch-scenario checks (criteria.md sections 1-3) on one snapshot of arch/riscv.

    python3 -B patch_rules.py scan SNAP OUT.json                     P1 and P2 on the whole of arch/riscv at SNAP
    python3 -B patch_rules.py ref BASE TARGET REFLIST OUT.json       P3: reference commits (arch/x86 parts) against
                                                                     the target series BASE..TARGET (arch/riscv parts)

P1 (reverse execution context): calls of CPU-local operations (fixmap, local TLB/icache flushes) not pinned to the
current CPU, followed up the callers at most three levels. P2 (variant completeness): non-static functions of one
member of a 32/64 file pair that the other member lacks while a __weak default exists or shared code calls them.
P3: hooks the reference overrides and common functions its arch changes newly call, each looked up in the target
series. The frozen version-4 machinery (ctx4.py: index, calls, regions, callbacks) is reused unchanged.
WSL; no model calls. Existing outputs are never overwritten.
"""
from pathlib import Path
import importlib.util
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
RULES_DIR = HERE.parent / 'rules_v4_tighten_20261103'
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions)
import modules as M  # noqa: E402  (defs_in, called_in_common)

RISCV = 'arch/riscv'
PIN_OPS = re.compile(r'__set_fixmap|set_fixmap|set_fixmap_offset|clear_fixmap'
                     r'|local_flush_tlb_page|local_flush_tlb_all|local_flush_tlb_range|local_flush_icache_all')
ASSERT = re.compile(r'lockdep_assert_irqs_disabled|lockdep_assert_preemption_disabled'
                    r'|(WARN_ON|WARN_ON_ONCE|BUG_ON)\s*\(\s*preemptible\s*\(')
DEPTH = 3
COMMON_DIRS = ('kernel', 'mm', 'lib', 'init', 'include', 'net', 'drivers', 'fs', 'block', 'virt')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Snap:
    def __init__(self, snap):
        self.snap = snap
        C = self.C = load('ctx4_p', RULES_DIR / 'ctx4.py')
        C.SNAP = snap
        idx, _ = C.build_index()
        C.INDEX.update(idx)
        self.callbacks = set()
        rv = C.riscv_defs()
        for d in rv:
            for c in C.calls(d):
                if C.CALLBACK_USERS.fullmatch(c.name):
                    self.callbacks |= {a.strip().lstrip('&') for a in c.args}
        self._callers = {}
        self.by_path = {}
        for ds in C.INDEX.values():
            for d in ds:
                self.by_path.setdefault(d['path'], []).append(d)

    def callers(self, name):
        """[(def, call)] for every call of name in arch/riscv and the indexed common directories."""
        if name in self._callers:
            return self._callers[name]
        out = []
        paths = CK.git('grep', '-l', '-w', name, self.snap, '--', RISCV, *self.C.DEF_DIRS[1:]).split()
        paths = {p.split(':', 1)[1] for p in paths}
        for p in sorted(paths):
            for d in self.by_path.get(p, []):
                if d['name'] != name and name in d['text']:
                    out += [(d, c) for c in self.C.calls(d) if c.name == name]
        self._callers[name] = out
        return out

    def pinned_in(self, d, call):
        """criteria 1.1-1.4: the call of d is pinned within d itself."""
        C = self.C
        if C.is_init(d) or ASSERT.search(d['text']) or d['name'] in self.callbacks:
            return True
        return any(call in cs for _, _, cs, _ in C.regions(d))


# ------------------------------------------------------------------ P1
def p1(S):
    flags = []
    for d in S.C.riscv_defs():
        for c in S.C.calls(d):
            if not PIN_OPS.fullmatch(c.name) or S.pinned_in(d, c):
                continue
            chain = unpinned_chain(S, d, 1, (d['name'],))
            if chain is not None:
                names, unknown = chain
                flags.append({'rule': 'P1', 'path': d['path'], 'name': d['name'], 'start': d['start'],
                              'end': d['end'], 'op': c.name, 'chain': names,
                              'reason': f'{c.name} not pinned to the CPU; caller chain {" <- ".join(names)}'
                                        + (' (upper callers unknown)' if unknown else ''),
                              'issue': f'P1|{d["path"]}:{d["name"]}|{c.name}'})
    return flags


def unpinned_chain(S, d, level, names):
    """A caller chain from d upwards on which no level is pinned (criteria 1.5), or None when every chain is pinned.
    Returns (names, upper_callers_unknown)."""
    if S.C.is_init(d) or ASSERT.search(d['text']) or d['name'] in S.callbacks:
        return None
    if level > DEPTH:
        return names, False
    sites = S.callers(d['name'])
    if not sites:
        return names, True
    for g, call in sites:
        if g['name'] in names or S.pinned_in(g, call):
            continue
        got = unpinned_chain(S, g, level + 1, names + (g['name'],))
        if got is not None:
            return got
    return None


# ------------------------------------------------------------------ P2
def variant_pairs(snap):
    files = [f for f in CK.git('ls-tree', '-r', '--name-only', snap, RISCV).splitlines() if f.endswith('.c')]
    have = set(files)
    pairs = []
    for f in files:
        base = f.rsplit('/', 1)[-1]
        if '64' in base:
            g = f[:len(f) - len(base)] + base.replace('64', '32')
            if g in have:
                pairs.append((f, g))
    return pairs


def p2(S):
    snap, flags = S.snap, []
    for a, b in variant_pairs(snap):
        folder = a.rsplit('/', 1)[0]
        members = {a, b}
        shared = [f for f in CK.git('ls-tree', '--name-only', snap, folder + '/').splitlines()
                  if f.endswith('.c') and f not in members
                  and not any(f == x for pair in variant_pairs(snap) for x in pair)]
        for this, other in ((a, b), (b, a)):
            mine = {n: (s, e, t) for s, e, n, t in CK.functions(snap, this)
                    if not re.search(r'(^|\W)static(\W|$)', t.split('{', 1)[0])}
            theirs = {n for _, _, n, _ in CK.functions(snap, other)}
            missing = sorted(n for n in mine if n not in theirs)
            if not missing:
                continue
            weak = weak_defaults(snap, missing)
            common = M.called_in_common(snap, missing)
            for n in missing:
                users = [f for f in shared if re.search(r'(^|[^A-Za-z0-9_])' + n + r'\s*\(',
                                                        CK.git('show', f'{snap}:{f}'))]
                why = []
                if n in weak:
                    why.append(f'__weak default in {weak[n]}')
                if users:
                    why.append('called from shared ' + ', '.join(users))
                if n in common:
                    why.append('called from common code')
                if why:
                    s, e, _ = mine[n]
                    flags.append({'rule': 'P2', 'path': this, 'name': n, 'start': s, 'end': e, 'missing_in': other,
                                  'reason': f'defined in {this}, not in {other}; ' + '; '.join(why),
                                  'issue': f'P2|{other}|{n}'})
    return flags


def weak_defaults(snap, names):
    out = {}
    for n in names:
        for h in CK.git('grep', '-n', '-E', r'__weak.*[^A-Za-z0-9_]' + n + r'[[:space:]]*\(', snap, '--', '*.c',
                        ':(exclude)arch', ':(exclude)tools').splitlines():
            out.setdefault(n, h.split(':')[1])
    return out


# ------------------------------------------------------------------ P3
IDENT_CALL = re.compile(r'(?<![A-Za-z0-9_>.])([A-Za-z_]\w*)\s*\(')
KEYWORDS = {'if', 'for', 'while', 'switch', 'return', 'sizeof', 'typeof', 'defined', '__attribute__', 'do'}


def added_calls(rev_a, rev_b, path):
    plus, minus = set(), set()
    for l in CK.git('diff', '-U0', rev_a, rev_b, '--', path).splitlines():
        if l.startswith('+') and not l.startswith('+++'):
            plus |= set(IDENT_CALL.findall(l))
        elif l.startswith('-') and not l.startswith('---'):
            minus |= set(IDENT_CALL.findall(l))
    return plus - minus - KEYWORDS


def changed_defs(rev_a, rev_b, path):
    """Names of functions at rev_b whose header line is an added line of rev_a..rev_b."""
    added = set()
    for l in CK.git('diff', '-U0', rev_a, rev_b, '--', path).splitlines():
        m = re.match(r'@@ -\S+ \+(\d+)(?:,(\d+))? ', l)
        if m:
            s0, n = int(m.group(1)), int(m.group(2) or 1)
            added |= set(range(s0, s0 + n))
    out = set()
    for f in CK.git('diff', '--name-only', rev_a, rev_b, '--', path).split():
        if f.endswith(('.c', '.h')):
            for s, e, name, t in CK.functions(rev_b, f):
                head_lines = t.split('{', 1)[0].count('\n') + 1
                if any(x in added for x in range(s - head_lines + 1, s + 1)):
                    out.add(name)
    return out


def p3(base, target, refs):
    hooks, calls = {}, {}
    for r in refs:
        par = r + '^'
        for n in changed_defs(par, r, 'arch/x86'):
            hooks.setdefault(n, r)
        for n in added_calls(par, r, 'arch/x86'):
            calls.setdefault(n, r)
    hooks = {n: r for n, r in hooks.items() if n in weak_defaults(target, [n])}
    common = M.defs_in(target, sorted(calls), ('*.c', '*.h', ':(exclude)arch', ':(exclude)tools'), macros=True)
    calls = {n: r for n, r in calls.items() if n in common}
    t_defs_by_file = {}
    for f in CK.git('diff', '--name-only', base, target, '--', RISCV).split():
        if f.endswith('.c'):
            t_defs_by_file[f] = {n for _, _, n, _ in CK.functions(target, f)}
    t_calls = added_calls(base, target, RISCV) | added_calls(base, target, 'kernel') | added_calls(base, target, 'include')
    rows = []
    for n, r in sorted(hooks.items()):
        where = sorted(f for f, ns in t_defs_by_file.items() if n in ns)
        rows.append({'kind': 'hook', 'name': n, 'reference': r, 'target_defined_in': where, 'found': bool(where)})
    for n, r in sorted(calls.items()):
        rows.append({'kind': 'call', 'name': n, 'reference': r, 'found': n in t_calls})
    return rows


def main():
    cmd = sys.argv[1]
    if cmd == 'scan':
        snap, out = sys.argv[2], Path(sys.argv[3])
        if out.exists():
            raise SystemExit('preserve')
        t0 = time.time()
        S = Snap(snap)
        t1 = time.time()
        f1 = p1(S)
        t2 = time.time()
        f2 = p2(S)
        stats = {'snapshot': snap, 'index_seconds': round(t1 - t0), 'P1': {'flags': len(f1), 'seconds': round(t2 - t1)},
                 'P2': {'flags': len(f2), 'seconds': round(time.time() - t2)}}
        out.write_text(json.dumps({'stats': stats, 'flags': f1 + f2}, indent=1, ensure_ascii=False) + '\n',
                       encoding='utf-8')
        print(json.dumps(stats))
    elif cmd == 'ref':
        base, target, reflist, out = sys.argv[2], sys.argv[3], Path(sys.argv[4]), Path(sys.argv[5])
        if out.exists():
            raise SystemExit('preserve')
        refs = [l.split()[0] for l in reflist.read_text(encoding='utf-8').splitlines() if l and not l.startswith('#')]
        rows = p3(base, target, refs)
        out.write_text(json.dumps({'base': base, 'target': target, 'rows': rows}, indent=1) + '\n', encoding='utf-8')
        print(sum(not r['found'] for r in rows), 'of', len(rows), 'without a counterpart')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
