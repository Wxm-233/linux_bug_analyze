"""Enumerate check points on the snapshot (criteria.md section 2) and report localisation recall (section 4.1,
no model calls). Labels are read only for the recall report. WSL. Output: points.json, localisation.json.
"""
from pathlib import Path
import json
import re
import time

import modules as M

HERE = Path(__file__).resolve().parent
SNAP, SNAP_DATE = 'v6.12', '2024-11-17'
LABELS = M.ROOT / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
EVAL = M.ROOT / 'method_eval_testset_20261102' / 'results.json'


def added_names(sha):
    """Function or macro names that the fix defines in arch/riscv ('+' lines)."""
    diff = M.git('show', '--format=', sha, '--', 'arch/riscv')
    names = set()
    for l in diff.splitlines():
        if not l.startswith('+') or l.startswith('+++'):
            continue
        m = re.match(r'\+\s*#\s*define\s+([A-Za-z_]\w*)', l) or re.match(r'\+[A-Za-z_].*?([A-Za-z_]\w*)\s*\(', l)
        if m:
            names.add(m.group(1))
    return names


def main():
    target = HERE / 'points.json'
    if target.exists():
        raise SystemExit('preserve')
    t0 = time.time()
    rv_all = M.riscv_defs(SNAP)
    rv_c = {n: [p for p in ps if p.endswith('.c')] for n, ps in rv_all.items()}
    rv_c = {n: ps for n, ps in rv_c.items() if ps}
    pts = {}
    pts['M10'] = M.m10_points(SNAP, rv_all)
    pts['M1'] = M.m1_points(SNAP)
    pts['M5'] = M.m5_points(SNAP)
    pts['M8'], m8_pairs = M.m8_points(SNAP, rv_c)
    pts['M2'] = M.m2_points(SNAP)
    target.write_text(json.dumps({'snapshot': SNAP, 'points': pts, 'm8_pairs_examined': m8_pairs}, indent=1,
                                 ensure_ascii=False) + '\n', encoding='utf-8')
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    funcs = {r['id']: r['functions'] for r in json.loads(EVAL.read_text(encoding='utf-8'))}
    pos = [r for r in labels if not r['dev'] and r['flag'] not in ('无关', '构建错误') and r['cross'] == 'C'
           and r['date'] > SNAP_DATE]
    keyset = {m: {(p['path'], p['name']) for p in ps if 'path' in p} for m, ps in pts.items()}
    m1_names = {p['name'] for p in pts['M1']}
    rows = []
    for r in pos:
        fx = {tuple(f.rsplit(':', 1)) for f in funcs.get(r['id'], [])}
        hit = {m: sorted(f'{a}:{b}' for a, b in fx & keyset[m]) for m in ('M10', 'M5', 'M8', 'M2')}
        hit['M1'] = sorted(added_names(r['commit']) & m1_names) if r['source'] == 'A' else []
        rows.append({'id': r['id'], 'mechanism': r['mechanism'], 'applicable': bool(fx),
                     'located_by': {m: v for m, v in hit.items() if v}})
    summary = {'positives_after_snapshot': len(pos), 'with_riscv_functions': sum(x['applicable'] for x in rows),
               'points': {m: len(ps) for m, ps in pts.items()}, 'm8_pairs_examined': m8_pairs,
               'located_any': sum(bool(x['located_by']) for x in rows),
               'located_by_module': {m: sum(m in x['located_by'] for x in rows) for m in pts},
               'by_mechanism': {}, 'seconds': round(time.time() - t0)}
    for mech in sorted({x['mechanism'] for x in rows}):
        xs = [x for x in rows if x['mechanism'] == mech]
        summary['by_mechanism'][mech] = {'n': len(xs), 'located_any': sum(bool(x['located_by']) for x in xs),
                                         'located_by_own_module': sum(mech in x['located_by'] for x in xs)}
    (HERE / 'localisation.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1,
                                                       ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
