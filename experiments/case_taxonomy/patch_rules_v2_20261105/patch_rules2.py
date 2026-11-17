"""Version 2 of P1 and P2 (criteria.md sections 1 and 2) on one snapshot of arch/riscv.

    python3 -B patch_rules2.py scan SNAP OUT.json

P1 v2 = version 1 (patch_rules_20261105/patch_rules.py, imported unchanged) plus: a call before the first
local_irq_enable of a trap handler is pinned; a call under a "fewer than two CPUs online" condition is pinned; a chain
is reported only when some level shows the context can sleep (a sleeping call before the next call, or
lockdep_assert_held on a mutex); depth 4. P2 v2 reports only functions a file shared by both variants calls.
WSL; no model calls. Existing outputs are never overwritten.
"""
from pathlib import Path
import importlib.util
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('patch_rules_v1', HERE.parent / 'patch_rules_20261105' / 'patch_rules.py')
V1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V1)
CK, RISCV = V1.CK, V1.RISCV

DEPTH = 4
SINGLE = re.compile(r'num_online_cpus\s*\(\s*\)\s*(<\s*2|==\s*1|<=\s*1)')
MULTI = re.compile(r'num_online_cpus\s*\(\s*\)\s*(>\s*1|>=\s*2|!=\s*1)')
HELD = re.compile(r'lockdep_assert_held\s*\(\s*&\s*([A-Za-z_]\w*)\s*\)')


class Snap2(V1.Snap):
    def __init__(self, snap):
        super().__init__(snap)
        self.handlers = set(self.C.trap_handlers())
        self._mutex = {}

    def is_mutex(self, name):
        if name not in self._mutex:
            hits = CK.git('grep', '-l', '-E', rf'DEFINE_MUTEX\({name}\)|struct mutex[[:space:]]+{name}[[:space:]]*[;=]',
                          self.snap, '--', '*.c', '*.h')
            self._mutex[name] = bool(hits.strip())
        return self._mutex[name]

    def pinned_in(self, d, call):
        if super().pinned_in(d, call):
            return True
        C = self.C
        if d['name'] in self.handlers and d['path'].startswith(RISCV):  # section 1.1
            pre = C.inside(C.calls(d), lambda n: False, lambda n: n == 'local_irq_enable', initially=True)
            if call in pre:
                return True
        for text, positive in call.conds:  # section 1.2
            if (SINGLE.search(text) and positive) or (MULTI.search(text) and not positive):
                return True
        return False

    def evidence(self, d, call):
        """Section 1.3: d can sleep before making call, or asserts that it holds a mutex."""
        if any(self.C.SLEEP.fullmatch(c.name) and c.line < call.line for c in self.C.calls(d)):
            return True
        return any(self.is_mutex(m.group(1)) for m in HELD.finditer(d['text']))


def chain(S, d, call, level, names):
    """An unpinned caller chain from d (which makes call) with evidence of a sleepable context, or None."""
    if S.C.is_init(d) or V1.ASSERT.search(d['text']) or d['name'] in S.callbacks:
        return None
    if S.evidence(d, call):
        return names
    if level >= DEPTH:
        return None
    for g, c in S.callers(d['name']):
        if g['name'] in names or S.pinned_in(g, c):
            continue
        got = chain(S, g, c, level + 1, names + (g['name'],))
        if got is not None:
            return got
    return None


def p1(S):
    flags = []
    for d in S.C.riscv_defs():
        for c in S.C.calls(d):
            if not V1.PIN_OPS.fullmatch(c.name) or S.pinned_in(d, c):
                continue
            names = chain(S, d, c, 1, (d['name'],))
            if names is not None:
                flags.append({'rule': 'P1', 'path': d['path'], 'name': d['name'], 'start': d['start'],
                              'end': d['end'], 'op': c.name, 'chain': list(names),
                              'reason': f'{c.name} not pinned to the CPU; sleepable caller chain {" <- ".join(names)}',
                              'issue': f'P1|{d["path"]}:{d["name"]}|{c.name}'})
    return flags


def p2(S):
    snap, flags = S.snap, []
    pairs = V1.variant_pairs(snap)
    in_pairs = {x for pair in pairs for x in pair}
    for a, b in pairs:
        folder = a.rsplit('/', 1)[0]
        shared = [f for f in CK.git('ls-tree', '--name-only', snap, folder + '/').splitlines()
                  if f.endswith('.c') and f not in in_pairs]
        texts = {f: CK.git('show', f'{snap}:{f}') for f in shared}
        for this, other in ((a, b), (b, a)):
            mine = {n: (s, e) for s, e, n, t in CK.functions(snap, this)
                    if not re.search(r'(^|\W)static(\W|$)', t.split('{', 1)[0])}
            theirs = {n for _, _, n, _ in CK.functions(snap, other)}
            for n in sorted(x for x in mine if x not in theirs):
                users = [f for f, t in texts.items() if re.search(r'(^|[^A-Za-z0-9_])' + n + r'\s*\(', t)]
                if users:
                    s, e = mine[n]
                    flags.append({'rule': 'P2', 'path': this, 'name': n, 'start': s, 'end': e, 'missing_in': other,
                                  'reason': f'defined in {this}, not in {other}; called from shared {", ".join(users)}',
                                  'issue': f'P2|{other}|{n}'})
    return flags


def main():
    if sys.argv[1] != 'scan':
        raise SystemExit(__doc__)
    snap, out = sys.argv[2], Path(sys.argv[3])
    if out.exists():
        raise SystemExit('preserve')
    t0 = time.time()
    S = Snap2(snap)
    t1 = time.time()
    f1 = p1(S)
    t2 = time.time()
    f2 = p2(S)
    stats = {'snapshot': snap, 'index_seconds': round(t1 - t0), 'P1': {'flags': len(f1), 'seconds': round(t2 - t1)},
             'P2': {'flags': len(f2), 'seconds': round(time.time() - t2)}}
    out.write_text(json.dumps({'stats': stats, 'flags': f1 + f2}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
