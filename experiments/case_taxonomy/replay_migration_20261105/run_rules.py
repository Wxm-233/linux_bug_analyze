"""Program checks for the RISC-V test patches (criteria.md section 4): the version-4 rules (patch_check_20261105's
scan) and P1/P2 version 2 (patch_rules_v2_20261105) on T^ and on every patched commit of commits_test.json; a flag
is reported when its issue key is not among T^'s. 4 scans at a time, PYTHONHASHSEED=0. WSL; no model calls.
Output: rules/<sha>_{v4,p2}.json and rules_test.json ({patch dir: [flags]}).
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
V4 = HERE.parent / 'patch_check_20261105' / 'patch_check.py'
P2 = HERE.parent / 'patch_rules_v2_20261105' / 'patch_rules2.py'
ENV = {**os.environ, 'PYTHONHASHSEED': '0'}


def scan(item):
    sha, kind = item
    out = HERE / 'rules' / f'{sha[:12]}_{kind}.json'
    if not out.exists():
        subprocess.run([sys.executable, '-B', str(V4 if kind == 'v4' else P2), 'scan', sha, str(out)], env=ENV,
                       check=True, stdout=subprocess.DEVNULL)
    return json.loads(out.read_text(encoding='utf-8'))['flags']


def main():
    if (HERE / 'rules_test.json').exists():
        raise SystemExit('preserve')
    (HERE / 'rules').mkdir(exist_ok=True)
    labels = {r['id']: r for r in json.loads((HERE.parent / 'replay_samples_more_20261105' / 'labels_all.json')
                                             .read_text(encoding='utf-8'))}
    commits = json.loads((HERE / 'commits_test.json').read_text(encoding='utf-8'))
    index = json.loads((HERE / 'prompt_index_test.json').read_text(encoding='utf-8'))
    todo = [(x['dir'], commits[x['dir']]) for x in index
            if labels[x['id']]['target_arch'] == 'riscv' and commits[x['dir']]['sha']]
    shas = sorted({c['base'] for _, c in todo} | {c['sha'] for _, c in todo})
    jobs = [(s, k) for s in shas for k in ('v4', 'p2')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        flags = dict(zip(jobs, pool.map(scan, jobs)))
    result = {}
    for d, c in todo:
        rows = []
        for k in ('v4', 'p2'):
            base_keys = {f['issue'] for f in flags[(c['base'], k)]}
            rows += [{'rule': f['rule'], 'function': f'{f["path"]}:{f["name"]}', 'reason': f['reason'],
                      'issue': f['issue']} for f in flags[(c['sha'], k)] if f['issue'] not in base_keys]
        result[d] = rows
        print(d, len(rows))
    (HERE / 'rules_test.json').write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
