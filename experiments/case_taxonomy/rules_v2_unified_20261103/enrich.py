"""Reference statistic (criteria.md section 4): share of flagged functions whose v6.1 range (signature included) a
Fixes commit in v6.1..v6.6 changed, against Random(20261110) 200 unflagged arch/riscv .c functions; plus, for the
flagged ones, the Fixes commits up to the end version. WSL. Output: enrich.json."""
from math import comb
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402


def fixes(path, s, e, lo, hi):
    out = []
    for sha in re.findall(r'^[0-9a-f]{40}$', CK.git('log', '--format=%H', '-s', '-L', f'{max(1, s - 4)},{e}:{path}',
                                                     f'{lo}..{hi}'), re.M):
        msg = CK.git('log', '-1', '--format=%s%n%b', sha)
        if re.search(r'^\s*Fixes:', msg, re.M | re.I):
            out.append(f'{sha[:12]} {msg.splitlines()[0][:80]}')
    return out


def fisher(a, b, c, d):
    n, r1, c1 = a + b + c + d, a + b, a + c
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    obs = p(a)
    return round(min(1.0, sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= obs * (1 + 1e-9))), 4)


def main():
    flags = json.loads((HERE / 'flags_eval_v6.1.json').read_text(encoding='utf-8'))['flags']
    flagged = sorted({(f['path'], f['name'], f['start'], f['end']) for f in flags})
    keys = {(p, n) for p, n, _, _ in flagged}
    pool = []
    for p in CK.git('ls-tree', '-r', '--name-only', 'v6.1', 'arch/riscv').splitlines():
        if p.endswith('.c'):
            pool += [(p, n, s, e) for s, e, n, _ in CK.functions('v6.1', p) if (p, n) not in keys]
    sample = random.Random(20261110).sample(pool, 200)
    rows = {'flagged': [[p, n, fixes(p, s, e, 'v6.1', 'v6.6'), fixes(p, s, e, 'v6.6', CK.END)] for p, n, s, e in flagged],
            'unflagged_sample': [[p, n, fixes(p, s, e, 'v6.1', 'v6.6')] for p, n, s, e in sample]}
    a, n1 = sum(bool(x[2]) for x in rows['flagged']), len(rows['flagged'])
    c, n2 = sum(bool(x[2]) for x in rows['unflagged_sample']), len(rows['unflagged_sample'])
    summary = {'flagged_fixed_in_window': [a, n1], 'unflagged_fixed_in_window': [c, n2],
               'fisher_p': fisher(a, n1 - a, c, n2 - c)}
    (HERE / 'enrich.json').write_text(json.dumps({'summary': summary, **rows}, indent=1, ensure_ascii=False) + '\n',
                                      encoding='utf-8')
    print(summary)
    for x in rows['flagged']:
        print(x)


if __name__ == '__main__':
    main()
