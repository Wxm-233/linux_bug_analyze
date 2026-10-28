"""A0 path-metadata admission for the frozen sample, and pilot selection from the reserve (run in WSL).
Reads only touched file paths; prints counts only."""
from pathlib import Path
import hashlib
import json
import random
import re
import subprocess

HERE = Path(__file__).resolve().parent
S1 = HERE.parent / 'unified_impl_stage1_20261027'
REPO = '/root/repos/linux'
RULES = [
    ('arch', re.compile(r'^arch/[^/]+/')),
    ('platform_driver', re.compile(r'^drivers/(acpi|of|firmware|xen|iommu|virtio|base)/')),
    ('asm_generic', re.compile(r'^include/asm-generic/')),
    ('core_header', re.compile(r'^include/linux/(cpumask|topology|smp|dma-[^/]*|iommu|acpi|of)[^/]*\.h$')),
]


def paths(h):
    out = subprocess.run(['git', '-C', REPO, 'show', '--name-only', '--format=', h], capture_output=True, text=True)
    return [p for p in out.stdout.splitlines() if p.strip()] if out.returncode == 0 else None


def a0(ps):
    if ps is None:
        return {'admitted': False, 'rule': 'unresolvable'}
    hits = sorted({name for p in ps for name, rx in RULES if rx.search(p)})
    arches = {p.split('/')[1] for p in ps if p.startswith('arch/') and p.count('/') >= 2}
    if len(arches) >= 2:
        hits.append('multi_arch')
    return {'admitted': bool(hits), 'rule': hits, 'files': len(ps),
            'paths_sha256': hashlib.sha256('\n'.join(ps).encode()).hexdigest()}


def main():
    target = HERE / 'a0_admission.json'
    if target.exists():
        raise SystemExit('preserve')
    sample = [l for l in (S1 / 'frozen_sample.txt').read_text().split() if l]
    rows = {h: a0(paths(h)) for h in sample}
    pool = json.loads((S1 / 'frozen_pool.json').read_text())
    cand = [l for l in (S1.parents[2] / 'candidate_hashes.txt').read_text().split() if l]
    excluded = set((S1 / 'contacted_candidates.txt').read_text().split()) | set((S1 / 'family_linked_candidates.txt').read_text().split()) | set(sample)
    reserve = sorted(set(cand) - excluded)
    rng = random.Random(20261028)
    order = reserve[:]
    rng.shuffle(order)
    pilot, examined = [], 0
    for h in order:
        examined += 1
        r = a0(paths(h))
        if r['admitted']:
            pilot.append({'hash': h, **r})
        if len(pilot) == 2:
            break
    out = {'sample_size': len(sample), 'admitted': sum(r['admitted'] for r in rows.values()),
           'rule_counts': {k: sum(k in r['rule'] for r in rows.values() if isinstance(r['rule'], list)) for k in [n for n, _ in RULES] + ['multi_arch']},
           'unresolvable': sum(r['rule'] == 'unresolvable' for r in rows.values()), 'rows': rows,
           'reserve_size': len(reserve), 'reserve_expected': pool['untouched'] - len(sample),
           'pilot_seed': 20261028, 'pilot_examined': examined, 'pilot': pilot,
           'contact_note': 'touched file paths were read for the 300 sample commits and the examined reserve commits; no subject, message or diff'}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ['sample_size', 'admitted', 'rule_counts', 'unresolvable', 'reserve_size', 'reserve_expected', 'pilot_examined']}))


if __name__ == '__main__':
    main()
