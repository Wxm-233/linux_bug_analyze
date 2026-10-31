"""RISC-V cases (criteria.md): T touches arch/riscv, its Fixes: names a common-layer C that did not touch riscv.
Same pairing rule as count_ccp.py restricted to riscv. Lists hashes, subjects and category. WSL. Output: riscv_cases.json."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
sys.path.insert(0, str(C_DIR / 'sibling_dataset_20261029'))
import build_dataset as BD  # noqa: E402

X = BD.X
P = X.body_targets.__globals__


def subject(c):
    return P['git']('show', '-s', '--format=%s', c).strip()


def main():
    target = HERE / 'riscv_cases.json'
    if target.exists():
        raise SystemExit('preserve')
    fixers = X.log_fixes()
    res = X.resolve({t for r in fixers.values() for t in r['fixes']})
    cache = dict(fixers)
    cases = []
    for t, r in fixers.items():
        if 'riscv' not in X.arches(r['files']):
            continue
        for tok in r['fixes']:
            c = res.get(tok)
            if not c or c.startswith(X.ROOT_COMMIT) or c == t:
                continue
            cm = X.meta_of(c, cache)
            if 'riscv' in X.arches(cm['files']) or not any(f.endswith(('.c', '.h')) and not f.startswith('arch/') for f in cm['files']):
                continue
            rv = [f for f in r['files'] if f.startswith('arch/riscv/')]
            tg = [y for y in BD.body_targets_strict(t, c) if y[0].startswith('arch/riscv/')] if any(f.endswith(('.c', '.h')) for f in rv) else []
            kind = ('existing_function' if tg else 'new_code_or_outside_function' if any(f.endswith(('.c', '.h')) for f in rv)
                    else 'no_c_or_h')
            cases.append({'seed': c, 'target': t, 'kind': kind, 'c_subject': subject(c), 't_subject': subject(t),
                          'riscv_files': rv, 'targets': tg})
            break
    target.write_text(json.dumps({'cases': cases}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(cases), {k: sum(1 for x in cases if x['kind'] == k) for k in ('existing_function', 'new_code_or_outside_function', 'no_c_or_h')})


if __name__ == '__main__':
    main()
