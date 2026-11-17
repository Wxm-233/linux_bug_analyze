"""Scoring of the scan (criteria.md section 4). WSL (git needed). Labels are read only here.
Output: flags.json, scores.json, manual_review_sample.json.
"""
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path
import json
import random
import re

import modules as M
from enumerate_points import EVAL, LABELS, SNAP, SNAP_DATE, added_names

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-02' / 'mech_scan_20261102'
END = 'df2908090cda'


def answer(d):
    p = CALLS / d / 'final.md'
    if not p.exists():
        return None
    text = p.read_text(encoding='utf-8', errors='replace')
    for m in reversed(list(re.finditer(r'\{[^{}]*\}', text, re.S))):
        try:
            return json.loads(m.group(0))
        except ValueError:
            continue
    return None


def fisher(a, b, c, d):
    n, r1, c1 = a + b + c + d, a + b, a + c
    if not n:
        return 1.0
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    obs = p(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return round(min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9))), 4)


def fixed_after(point):
    """A Fixes-tagged commit in SNAP..END touching arch/riscv that changed the point (M1: added a RISC-V version of
    the default or changed a RISC-V function calling it is approximated by defining the name)."""
    if point['module'] == 'M1':
        out = M.git('log', '--format=%H', '--grep=Fixes:', f'{SNAP}..{END}', '-G',
                    r'(#[[:space:]]*define[[:space:]]+|[^A-Za-z0-9_])' + point['name'] + r'([^A-Za-z0-9_]|$)', '--', 'arch/riscv')
        return out.split()[0][:12] if out.split() else None
    out = M.git('log', '--format=%H', '-s', '-L', f':{point["name"]}:{point["path"]}', f'{SNAP}..{END}')
    for sha in re.findall(r'^[0-9a-f]{40}$', out, re.M):
        if re.search(r'^\s*Fixes:', M.git('log', '-1', '--format=%B', sha), re.M | re.I):
            return sha[:12]
    return None


def main():
    idx = json.loads((HERE / 'prompt_index.json').read_text(encoding='utf-8'))
    pts = json.loads((HERE / 'points.json').read_text(encoding='utf-8'))['points']
    rows = []
    for it in idx['items']:
        if not it.get('dir'):
            continue
        a = answer(it['dir'])
        v = (a or {}).get(it['verdict_key'])
        lines = [x for x in (a or {}).get('lines') or [] if isinstance(x, int)]
        ok = any(it['range'][0] <= x <= it['range'][1] for x in lines)
        rows.append({'module': it['module'], 'dir': it['dir'], 'point': it['point'], 'answered': a is not None,
                     'verdict': v, 'flag': v == 'yes' and ok, 'why': (a or {}).get('why', '')})
    rows += [{'module': 'M2', 'dir': None, 'point': p, 'answered': True, 'verdict': 'rule', 'flag': True, 'why': ''}
             for p in pts['M2']]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for r, fx in zip(rows, pool.map(lambda r: fixed_after(r['point']), rows)):
            r['fixed_after'] = fx
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    funcs = {r['id']: r['functions'] for r in json.loads(EVAL.read_text(encoding='utf-8'))}
    pos = [r for r in labels if not r['dev'] and r['flag'] not in ('无关', '构建错误') and r['cross'] == 'C'
           and r['date'] > SNAP_DATE]
    hits = []
    for p in pos:
        fx = {tuple(f.rsplit(':', 1)) for f in funcs.get(p['id'], [])}
        names = added_names(p['commit']) if p['source'] == 'A' else set()
        for r in rows:
            if not r['flag']:
                continue
            pt = r['point']
            if (pt['module'] == 'M1' and pt['name'] in names) or \
                    (pt['module'] != 'M1' and (pt['path'], pt['name']) in fx):
                hits.append({'id': p['id'], 'module': r['module'], 'point': pt.get('path', pt.get('default_path')) +
                             ':' + pt['name']})
    out = {'sampled': idx['sampled'], 'modules': {}, 'hits': hits, 'positives_after_snapshot': len(pos)}
    for m in ('M1', 'M5', 'M8', 'M10', 'M2'):
        rs = [r for r in rows if r['module'] == m]
        fl, uf = [r for r in rs if r['flag']], [r for r in rs if not r['flag']]
        a, c = sum(bool(r['fixed_after']) for r in fl), sum(bool(r['fixed_after']) for r in uf)
        out['modules'][m] = {'points_asked': len(rs), 'no_answer': sum(not r['answered'] for r in rs),
                             'yes': sum(r['verdict'] == 'yes' for r in rs), 'flags': len(fl),
                             'flagged_fixed_after': [a, len(fl)], 'unflagged_fixed_after': [c, len(uf)],
                             'fisher_p': fisher(a, len(fl) - a, c, len(uf) - c),
                             'hits': sorted({h['id'] for h in hits if h['module'] == m})}
    (HERE / 'flags.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    rnd, sample = random.Random(20261105), []
    for m in ('M1', 'M5', 'M8', 'M10'):
        fl = [r for r in rows if r['module'] == m and r['flag']]
        sample += fl if len(fl) <= 10 else rnd.sample(fl, 10)
    (HERE / 'manual_review_sample.json').write_text(json.dumps(sample, indent=1, ensure_ascii=False) + '\n',
                                                    encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'hits'}, indent=1, ensure_ascii=False), len(hits))


if __name__ == '__main__':
    main()
