"""Metadata-only description of the 103 unique sibling candidates (plan.md section 3). WSL for S's file list; no diffs or
messages are read. Output: dataset_stats.json; prints it.
"""
from collections import Counter
from pathlib import Path
import datetime
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
C = HERE.parent
ARCH = re.compile(r'^arch/([^/]+)/([^/]+)')


def s_arches(seed):
    files = subprocess.run(['git', '-C', '/root/repos/linux', 'show', '--name-only', '--format=', seed], capture_output=True, text=True).stdout.split()
    return sorted({ARCH.match(f).group(1) for f in files if f.endswith(('.c', '.h')) and ARCH.match(f)})


def main():
    target = HERE / 'dataset_stats.json'
    if target.exists():
        raise SystemExit('preserve')
    rows = [f for f in json.loads((C / 'sibling_dataset_20261029' / 'sibling_dataset.json').read_text())['pairs']
            if f['dup_of'] is None and not f['self_duplicate']]
    pairs, subdirs, years, ntargets = Counter(), Counter(), Counter(), Counter()
    for f in rows:
        sa = '+'.join(s_arches(f['seed'])) or '-'
        for ta in sorted({ARCH.match(p).group(1) for p, _ in f['xarch_targets']}):
            pairs['%s -> %s' % (sa, ta)] += 1
        for sub in {ARCH.match(p).group(2) for p, _ in f['xarch_targets']}:
            subdirs[sub] += 1
        years[datetime.datetime.utcfromtimestamp(f['time_t']).year] += 1
        n = len(f['xarch_targets'])
        ntargets['1' if n == 1 else '2-5' if n <= 5 else '6+'] += 1
    out = {'unique_pairs': len(rows), 'by_type': dict(Counter(f['type'] for f in rows)),
           'arch_pairs_top10': pairs.most_common(10), 'distinct_arch_pairs': len(pairs),
           'target_subdirs': subdirs.most_common(), 't_year': dict(sorted(years.items())), 'targets_per_pair': dict(ntargets),
           'different_author': sum(f['different_author'] for f in rows)}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
