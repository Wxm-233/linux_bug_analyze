"""Reference statistic (criteria.md section 3.3): share of flagged RISC-V functions whose v6.12 line range a
Fixes-tagged commit in v6.12..END changed, against Random(20261108) 200 unflagged arch/riscv .c functions. WSL."""
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402

SNAP, END = 'v6.12', CK.END


def fixed_later(path, s, e):
    out = CK.git('log', '--format=%H', '-s', '-L', f'{s},{e}:{path}', f'{SNAP}..{END}')
    for sha in re.findall(r'^[0-9a-f]{40}$', out, re.M):
        if re.search(r'^\s*Fixes:', CK.git('log', '-1', '--format=%B', sha), re.M | re.I):
            return sha[:12]
    return None


def main():
    flags = json.loads((HERE / 'flags_run2.json').read_text(encoding='utf-8'))['flags']
    flagged = sorted({(f['path'], f['function'], f['start'], f['end']) for f in flags})
    keys = {(p, n) for p, n, _, _ in flagged}
    pool = []
    for p in CK.git('ls-tree', '-r', '--name-only', SNAP, 'arch/riscv').splitlines():
        if p.endswith('.c'):
            pool += [(p, n, s, e) for s, e, n, _ in CK.functions(SNAP, p) if (p, n) not in keys]
    sample = random.Random(20261108).sample(pool, 200)
    rows = {'flagged': [[p, n, fixed_later(p, s, e)] for p, n, s, e in flagged],
            'unflagged_sample': [[p, n, fixed_later(p, s, e)] for p, n, s, e in sample]}
    summary = {k: [sum(bool(x[2]) for x in v), len(v)] for k, v in rows.items()}
    (HERE / 'later_fixed.json').write_text(json.dumps({'summary': summary, **rows}, indent=1) + '\n', encoding='utf-8')
    print(summary)
    for x in rows['flagged']:
        print(x)


if __name__ == '__main__':
    main()
