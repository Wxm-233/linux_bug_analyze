"""Run P1/P2 version 2 on every version of patch_check_20261105's series (P, U, Ufix) and on the end version
(criteria.md section 4). Versions are the same commits as before; each is checked to exist first. 4 scans at a
time, PYTHONHASHSEED=0. WSL; no model calls. Output: results/flags_<series>_<tag>.json, results/flags_end.json,
results/summary.json.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'patch_check_20261105' / 'results'
OUT = HERE / 'results'
END = 'df2908090cda'
P3_STATES = {}
ENV = {**os.environ, 'PYTHONHASHSEED': '0'}


def versions():
    out = []
    for name in ('P', 'U', 'Ufix'):
        cj = json.loads((PREV / name / 'commits.json').read_text(encoding='utf-8'))
        out.append((name, 'base', cj['base'], cj['base']))
        out += [(name, f'step{s["step"]}', s['sha'], cj['base']) for s in cj['steps']]
    return out


def sh(*a):
    subprocess.run([sys.executable, '-B', str(HERE / 'patch_rules2.py'), *a], env=ENV, check=True)


def main():
    OUT.mkdir(exist_ok=True)
    vs = versions()
    for _, _, sha, _ in vs:
        if subprocess.run(['git', '-C', '/root/repos/linux', 'cat-file', '-e', sha + '^{commit}']).returncode:
            raise SystemExit(f'{sha} missing; rebuild the series with patch_check_20261105/patch_check.py series')
    jobs = [('scan', sha, str(OUT / f'flags_{n}_{t}.json')) for n, t, sha, _ in vs]
    jobs.append(('scan', END, str(OUT / 'flags_end.json')))
    jobs = [j for j in jobs if not Path(j[2]).exists()]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda j: sh(*j), jobs))
    for n, t, sha, base in vs:
        if t in P3_STATES.get(n, []) and not (OUT / f'p3_{n}_{t}.json').exists():
            sh('ref', base, sha, str(HERE / 'input' / 'reference_x86.txt'), str(OUT / f'p3_{n}_{t}.json'))
    summary = {}
    for n, t, sha, _ in vs:
        d = json.loads((OUT / f'flags_{n}_{t}.json').read_text(encoding='utf-8'))
        summary[f'{n}_{t}'] = {'sha': sha, 'stats': d['stats'],
                               'issues': sorted({f['issue'] for f in d['flags']})}
        p3 = OUT / f'p3_{n}_{t}.json'
        if p3.exists():
            summary[f'{n}_{t}']['p3_missing'] = [r for r in json.loads(p3.read_text(encoding='utf-8'))['rows']
                                                 if not r['found']]
    end = json.loads((OUT / 'flags_end.json').read_text(encoding='utf-8'))
    summary['end'] = {'sha': END, 'stats': end['stats'], 'issues': sorted({f['issue'] for f in end['flags']})}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: (v['stats']['P1']['flags'], v['stats']['P2']['flags']) for k, v in summary.items()}))


if __name__ == '__main__':
    main()
