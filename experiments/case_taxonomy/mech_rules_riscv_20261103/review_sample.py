"""Precision sample (criteria.md section 3.3): Random(20261109) up to 12 flags per new rule of flags_run2.json, each
with the Fixes-tagged commits in v6.6..END that later changed its line range (supporting evidence for the manual
check, not a metric). WSL. Output: review_sample.json."""
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
import modules as M  # noqa: E402

SNAP, END = 'v6.6', 'df2908090cda'


def later_fixes(path, s, e):
    out = []
    for sha in re.findall(r'^[0-9a-f]{40}$', M.git('log', '--format=%H', '-s', '-L', f'{s},{e}:{path}',
                                                  f'{SNAP}..{END}'), re.M):
        msg = M.git('log', '-1', '--format=%s%n%b', sha)
        if re.search(r'^\s*Fixes:', msg, re.M | re.I):
            out.append(f'{sha[:12]} {msg.splitlines()[0][:90]}')
    return out


def main():
    flags = json.loads((HERE / 'flags_run2.json').read_text(encoding='utf-8'))['flags']
    rnd, rows = random.Random(20261109), []
    for rule in ('R1', 'R7', 'R8', 'R10'):
        fs = [f for f in flags if f['rule'] == rule]
        for f in (fs if len(fs) <= 12 else rnd.sample(fs, 12)):
            rows.append({**{k: f[k] for k in ('rule', 'path', 'name', 'start', 'end', 'reason')},
                         'later_fixes': later_fixes(f['path'], f['start'], f['end'])})
    (HERE / 'review_sample.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for i, r in enumerate(rows):
        print(i, r['rule'], f'{r["path"]}:{r["name"]}', '|', r['reason'][:150], '|', r['later_fixes'][:2])


if __name__ == '__main__':
    main()
