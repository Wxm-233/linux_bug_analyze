"""Hits by line range (criteria.md section 3.1). WSL (git). Default: development positives only; --eval scores the
evaluation positives once (scores_eval.json). Usage: python3 score.py FLAGS.json [--eval]
A fix's old-side changed lines at fix^ are mapped back to the snapshot through `git diff SNAP fix^ -- path`;
a flag hits when a mapped line of the same path falls in the flag's [start, end] or, for CTX, in a function on
its chain. R1 hits when the fix adds a riscv definition of the flagged default's name.
"""
from functools import lru_cache
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
import modules as M  # noqa: E402
from enumerate_points import added_names  # noqa: E402

SNAP, SNAP_DATE, WIN_END = 'v6.6', '2023-10-30', '2024-11-17'
LABELS = HERE.parent / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
MECH = {'R1': 'M1', 'R7': 'M7', 'R8': 'M8', 'R10': 'M10', 'CTX': 'M5'}


def hunks(args):
    out = []
    for m in re.finditer(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', M.git(*args), re.M):
        a, b = int(m.group(1)), int(m.group(2)) if m.group(2) is not None else 1
        c, d = int(m.group(3)), int(m.group(4)) if m.group(4) is not None else 1
        out.append((a, b, c, d))
    return out


def to_snap(path, sha, lines):
    """Map line numbers of path at sha^ to the snapshot."""
    if not M.git('ls-tree', SNAP, path).strip():
        return set()
    hs = hunks(['diff', '-U0', SNAP, sha + '^', '--', path])
    out = set()
    for n in lines:
        delta, mapped = 0, None
        for a, b, c, d in hs:
            if d and c <= n <= c + d - 1:  # inside lines the later commits changed: map to the snapshot's hunk
                mapped = set(range(a, a + b)) if b else {a}
                break
            old_next, new_next = (a + b if b else a + 1), (c + d if d else c + 1)
            if n >= new_next:
                delta = old_next - new_next
            else:
                break
        out |= mapped if mapped is not None else {n + delta}
    return out


@lru_cache(maxsize=None)
def fix_lines(sha):
    """{path: set(snapshot lines)} touched by the fix."""
    out, path = {}, None
    for l in M.git('show', '--format=', '-U0', sha).splitlines():
        if l.startswith('--- a/'):
            path = l[6:]
        elif l.startswith('--- '):
            path = None
        m = re.match(r'@@ -(\d+)(?:,(\d+))? ', l)
        if m and path:
            s, n = int(m.group(1)), int(m.group(2)) if m.group(2) is not None else 1
            old = set(range(s, s + n)) if n else {s, s + 1}
            out.setdefault(path, set()).update(to_snap(path, sha, old))
    return out


@lru_cache(maxsize=None)
def func_range(path, name):
    for s, e, n, _ in M.funcs(SNAP, path):
        if n == name:
            return s, e
    return None


def hit(flag, r):
    if flag['rule'] == 'R1':
        return r['source'] == 'A' and flag['name'] in added_names(r['commit'])
    fl = fix_lines(r['commit'])
    spans = [(flag['path'], flag['start'], flag['end'])]
    for c in flag.get('chain') or []:
        rg = func_range(c[0], c[1])
        if rg:
            spans.append((c[0], rg[0], rg[1]))
    return any(any(s <= x <= e for x in fl.get(p, ())) for p, s, e in spans)


def main():
    flags_file, evaluate = sys.argv[1], '--eval' in sys.argv[2:]
    flags = json.loads((HERE / flags_file).read_text(encoding='utf-8'))['flags']
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    pos = [r for r in labels if r['cross'] == 'C' and r['flag'] not in ('无关', '构建错误')
           and SNAP_DATE <= r['date'] <= WIN_END and r['dev'] != evaluate]
    rows = []
    for r in pos:
        hs = [f for f in flags if hit(f, r)]
        rows.append({'id': r['id'], 'mechanism': r['mechanism'], 'hit_rules': sorted({f['rule'] for f in hs}),
                     'hits': [{'rule': f['rule'], 'where': f'{f["path"]}:{f["name"]}', 'reason': f['reason'][:200]}
                              for f in hs[:8]]})
    by_rule = {}
    for rule, mech in MECH.items():
        n = sum(1 for f in flags if f['rule'] == rule)
        ids = [x['id'] for x in rows if rule in x['hit_rules']]
        by_rule[rule] = {'flags': n, 'hit': ids, 'hit_own_mechanism': [x['id'] for x in rows if rule in x['hit_rules']
                                                                        and x['mechanism'] == mech]}
    out = {'split': 'eval' if evaluate else 'dev', 'flags_file': flags_file, 'positives': len(pos),
           'by_rule': by_rule, 'rows': rows}
    name = 'scores_eval.json' if evaluate else f'scores_dev_{Path(flags_file).stem}.json'
    if evaluate and (HERE / name).exists():
        raise SystemExit('evaluation already scored once; preserve')
    (HERE / name).write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1, ensure_ascii=False))
    for x in rows:
        if x['hit_rules']:
            print(x['id'], x['mechanism'], x['hits'][:3])


if __name__ == '__main__':
    main()
