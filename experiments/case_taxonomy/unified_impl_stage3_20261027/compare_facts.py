"""Compare facts produced by the migrated package adapters (run2 evidence) with the facts the original
experiment scripts stored. Read-only."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
CASES = HERE.parent
EV = HERE / 'run2' / 'evidence'
load = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))


def originals():
    out = {}
    for p in (CASES / 'acpi_env_classification_20261027/analysis').glob('*.observation.json'):
        out[('acpi_env', p.name.split('.')[0])] = load(p)['facts']
    for p in (CASES / 'sparc_identity_chain_20261027/analysis').glob('*.facts.json'):
        out[('sparc_identity_chain', p.name[:-len('.facts.json')])] = load(p)['program_facts']
    rep = CASES / 'unified_impl_stage2_20261027/reproduction'
    for p in rep.glob('smmu_*.json'):
        out[('smmu_qtest', p.stem[len('smmu_'):])] = load(p)['facts']
    for p in rep.glob('virtio_*.json'):
        out[('virtio_split_trace', p.stem[len('virtio_'):])] = load(p)['facts']
    for p in rep.glob('layout_*.json'):
        if 'zero_granule' not in p.stem:
            out[('virtio_layout', p.stem[len('layout_'):])] = load(p)['facts']
    return out


def main():
    orig = originals()
    btrfs = load(CASES / 'btrfs_method_20261026/results.json')['diagnostics']
    for d in btrfs:
        orig[('btrfs_min', '%s_%d_%d_%d' % (d['mode'], d['page_size'], d['disk_sector_size'], d['request']))] = \
            {'request': d['request'], 'effective': d['effective'], 'geometry': d['disk_sector_size']}
    rows, compared, same = [], 0, 0
    for case_dir in sorted(p for p in EV.iterdir() if p.is_dir()):
        for f in sorted(case_dir.glob('*.json')):
            key = (case_dir.name, f.stem)
            if key not in orig:
                rows.append({'case': key[0], 'input': key[1], 'original': 'none'})
                continue
            compared += 1
            new = load(f)['facts']
            equal = new == orig[key]
            same += equal
            if not equal:
                rows.append({'case': key[0], 'input': key[1], 'diff_keys': sorted(k for k in set(new) | set(orig[key]) if new.get(k) != orig[key].get(k))})
    out = {'compared': compared, 'identical': same, 'notes': rows}
    (HERE / 'facts_comparison.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'compared': compared, 'identical': same, 'uncompared_or_diff': len(rows)}), rows[:5])


if __name__ == '__main__':
    main()
