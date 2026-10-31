"""Direction 1, part 2 (criteria.md): value pilot. 30 candidate sites in .c files, evaluated with kernel_facts.collect
(expr_values) under five architecture configurations. WSL; run from the code root. Output: pilot.json; prints counts.
"""
from pathlib import Path
import json
import random
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from linux_bug_analyze import kernel_facts as KF  # noqa: E402

END = 'df2908090cda'
CONFIGS = [('x86_64', 'x86', 'x86_64_defconfig', {}, ''),
           ('arm64', 'arm64', 'defconfig', {}, 'aarch64-linux-gnu-'),
           ('arm64_64k', 'arm64', 'defconfig', {'ARM64_64K_PAGES': True}, 'aarch64-linux-gnu-'),
           ('riscv', 'riscv', 'defconfig', {}, 'riscv64-linux-gnu-'),
           ('s390', 's390', 'defconfig', {}, 's390x-linux-gnu-')]
TMP = Path('/tmp/lba_rel')


def split_top(expr):
    """(lhs, op, rhs) at the first top-level comparison, or None."""
    depth, i, n = 0, 0, len(expr)
    while i < n:
        two = expr[i:i + 2]
        ch = expr[i]
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif depth == 0 and two in ('->', '<<', '>>'):
            i += 2
            continue
        elif depth == 0 and two in ('<=', '>=', '==', '!='):
            return expr[:i].strip(), two, expr[i + 2:].strip()
        elif depth == 0 and ch in '<>':
            return expr[:i].strip(), ch, expr[i + 1:].strip()
        i += 1
    return None


def main():
    target = HERE / 'pilot.json'
    if target.exists():
        raise SystemExit('preserve')
    sites = [s for s in json.loads((HERE / 'relations.json').read_text())['sites'] if s['candidate'] and s['path'].endswith('.c')]
    sites.sort(key=lambda s: (s['path'], s['line'], s['cond']))
    sample = random.Random(20261030).sample(sites, 30)
    for n, s in enumerate(sample, 1):
        s['n'] = n
        s['expr'] = s['cond'].replace('\\ ', ' ')
        parts = split_top(s['expr'])
        s['lhs'], s['op'], s['rhs'] = parts if parts else (None, None, None)
        s['probe'] = [e for e in (s['expr'], s['lhs'], s['rhs']) if e]
    by_file = {}
    for s in sample:
        by_file.setdefault(s['path'], []).append(s)
    shutil.rmtree(TMP, ignore_errors=True)
    results = {}
    for name, arch, defconfig, cfg, cross in CONFIGS:
        for k, (path, ss) in enumerate(sorted(by_file.items())):
            spec = {'revision': END, 'arch': arch, 'defconfig': defconfig, 'config_set': cfg, 'cross_compile': cross,
                    'files': [path], 'expr_values': sorted({e for s in ss for e in s['probe']})}
            out = TMP / name / str(k)
            try:
                KF.collect(spec, out)
                entry = json.loads((out / 'bundle.json').read_text())['files'][path]
            except Exception as exc:  # a failed defconfig/build is recorded, not retried
                entry = {'error': repr(exc)[:300]}
            for s in ss:
                vals = entry.get('expr_values') or {}
                results.setdefault(s['n'], {})[name] = {
                    'kbuild_selected': (entry.get('kbuild_selected') or {}).get('value'), 'build_returncode': entry.get('build_returncode'),
                    'error': entry.get('error'), 'values': {e: vals.get(e) for e in s['probe']}}
            print('done', name, k + 1, len(by_file), flush=True)
    target.write_text(json.dumps({'sample': sample, 'results': {str(k): v for k, v in results.items()}}, indent=1) + '\n')
    print('written', len(sample))


if __name__ == '__main__':
    main()
