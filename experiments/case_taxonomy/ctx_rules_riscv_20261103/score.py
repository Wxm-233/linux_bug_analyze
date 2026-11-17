"""Hits of a flags file on the positives fixed after the snapshot (criteria.md section 3.1-3.2). WSL (git).
Default: the development positives only. The test positives are scored only with --test, which writes
scores_test.json once (the frozen run). A positive's functions are the labelled ones plus the functions that hold
the fix's old-side hunks at the fix's parent; a flag hits when its owner or a function on its chain has the same
name and either the same path or both are under arch/riscv.
Usage: python3 score.py FLAGS.json [--test]
"""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402

LABELS = HERE.parent / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
SNAP_DATE = '2024-11-17'


def fixed_functions(r):
    out = {tuple(f.rsplit(':', 1)) for f in r['functions']}
    sha = r['commit']
    diff = CK.git('show', '--format=', '-U0', sha)
    path = None
    for l in diff.splitlines():
        if l.startswith('--- a/'):
            path = l[6:]
        elif l.startswith('--- '):
            path = None
        m = re.match(r'@@ -(\d+)(?:,(\d+))? ', l)
        if m and path and path.endswith(('.c', '.h')):
            s = int(m.group(1))
            n = int(m.group(2)) if m.group(2) is not None else 1
            for fs, fe, name, _ in CK.functions(sha + '^', path):
                if fs - 8 <= s <= fe or (n and fs <= s + n - 1 and s <= fe):
                    out.add((path, name))
    return out


def same(a, b):
    return a[1] == b[1] and (a[0] == b[0] or (a[0].startswith('arch/riscv') and b[0].startswith('arch/riscv')))


def hits_for(r, flags):
    fx = fixed_functions(r)
    out = []
    for f in flags:
        fns = [(f['path'], f['function'])] + [(c[0], c[1]) for c in f['chain']]
        if any(same(a, b) for a in fns for b in fx):
            out.append({'kind': f['kind'], 'source': f['source'], 'function': f'{f["path"]}:{f["function"]}',
                        'line': f['line'], 'sink': f['sink']})
    return sorted(fx), out


def main():
    flags_file, test = sys.argv[1], '--test' in sys.argv[2:]
    flags = json.loads((HERE / flags_file).read_text(encoding='utf-8'))['flags']
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    pos = [r for r in labels if r['cross'] == 'C' and r['flag'] not in ('无关', '构建错误') and r['date'] > SNAP_DATE
           and r['dev'] != test]
    rows = []
    for r in pos:
        fx, hs = hits_for(r, flags)
        rows.append({'id': r['id'], 'mechanism': r['mechanism'], 'fixed_functions': [f'{a}:{b}' for a, b in fx],
                     'hit': bool(hs), 'hits': hs[:10]})
    m5 = [x for x in rows if x['mechanism'] == 'M5']
    out = {'split': 'test' if test else 'dev', 'flags_file': flags_file, 'positives': len(rows),
           'hit': sum(x['hit'] for x in rows), 'm5': len(m5), 'm5_hit': sum(x['hit'] for x in m5),
           'hit_ids': [x['id'] for x in rows if x['hit']], 'rows': rows}
    if test:
        target = HERE / 'scores_test.json'
        if target.exists():
            raise SystemExit('test already scored once; preserve')
        target.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    else:
        (HERE / f'scores_dev_{Path(flags_file).stem}.json').write_text(
            json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1, ensure_ascii=False))
    for x in rows:
        if x['mechanism'] == 'M5' or x['hit']:
            print(x['id'], x['mechanism'], x['hit'], x['fixed_functions'][:4], x['hits'][:2])


if __name__ == '__main__':
    main()
