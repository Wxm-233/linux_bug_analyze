"""Read-only scan: which experiment directories use the common contract core, which relation operators,
symbol types, evidence bases and outcomes appear per mechanism, and how large the local adapters are."""
from pathlib import Path
from collections import Counter, defaultdict
import json
import re

HERE = Path(__file__).resolve().parent
CASES = HERE.parent
INNER = HERE.parents[2]

MECHANISMS = {
    'topology_preparation': [r'^cpu_topology', r'^cpu_method_', r'^s390_', r'^arch_contract_gate', r'^runtime_evidence_alignment', r'^contrast_selection', r'^evidence_feature_bridge'],
    'source_qualified_export': [r'^die_', r'^cpu_source_policy', r'^cpu_export_', r'^runtime_source_binding'],
    'btrfs_geometry': [r'^btrfs_'],
    'smmu_invalidation': [r'^smmu_'],
    'virtio_dma': [r'^virtio_'],
    'cpu_identity_range': [r'^cpu_identity', r'^cpu_mapping', r'^cpu_domain', r'^cpu_stage', r'^cpu_write', r'^cpu_independent', r'^sparc_'],
    'firmware_platform': [r'^acpi_', r'^firmware_platform'],
}


def mechanism_of(name):
    for mech, pats in MECHANISMS.items():
        if any(re.search(p, name) for p in pats):
            return mech
    return None


def walk(node, ops, syms):
    if isinstance(node, dict):
        if 'op' in node and isinstance(node.get('args'), list):
            ops[node['op']] += 1
        for v in node.values():
            walk(v, ops, syms)
    elif isinstance(node, list):
        for v in node:
            walk(v, ops, syms)


def contracts_in(obj, acc):
    if isinstance(obj, dict):
        if obj.get('schema') == 'architecture_contract_v1':
            acc.append(obj)
        else:
            for v in obj.values():
                contracts_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            contracts_in(v, acc)


def main():
    per = defaultdict(lambda: {'dirs': [], 'core_using_dirs': [], 'contracts': 0, 'ops': Counter(), 'symbol_types': Counter(),
                               'symbol_roles': Counter(), 'authority': Counter(), 'bases': Counter(), 'outcomes': Counter(),
                               'py_files': 0, 'py_lines': 0, 'dedicated_checkers': [], 'control_dirs': 0})
    for d in sorted(p for p in CASES.iterdir() if p.is_dir()):
        mech = mechanism_of(d.name)
        if not mech:
            continue
        m = per[mech]
        m['dirs'].append(d.name)
        uses = False
        for py in d.rglob('*.py'):
            if '__pycache__' in py.parts:
                continue
            text = py.read_text(encoding='utf-8', errors='replace')
            m['py_files'] += 1
            m['py_lines'] += text.count('\n')
            if 'contract_protocol' in text:
                uses = True
            if re.search(r'def (check|decide|judge|assess)\w*\(', text) and 'contract_protocol' not in text:
                m['dedicated_checkers'].append(py.relative_to(CASES).as_posix())
        if uses:
            m['core_using_dirs'].append(d.name)
        if any(x.is_dir() and 'control' in x.name for x in d.iterdir()):
            m['control_dirs'] += 1
        seen = set()
        for js in d.rglob('*.json'):
            if js.stat().st_size > 30_000_000:
                continue
            try:
                obj = json.loads(js.read_text(encoding='utf-8'))
            except Exception:
                continue
            found = []
            contracts_in(obj, found)
            for c in found:
                key = (c.get('id'), json.dumps(c.get('relation'), sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                m['contracts'] += 1
                walk(c.get('relation'), m['ops'], None)
                walk(c.get('scope'), m['ops'], None)
                for s in (c.get('symbols') or {}).values():
                    m['symbol_types'][s.get('type')] += 1
                    m['symbol_roles'][s.get('role')] += 1
                m['authority'][c.get('authority_kind')] += 1
            for rec in _records(obj):
                m['bases'][rec] += 1
            for out in _outcomes(obj):
                m['outcomes'][out] += 1
    result = {}
    for mech in MECHANISMS:
        m = per[mech]
        result[mech] = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in m.items()}
        result[mech]['dirs'] = len(m['dirs'])
        result[mech]['core_using_dir_count'] = len(m['core_using_dirs'])
        result[mech]['dedicated_checker_count'] = len(m['dedicated_checkers'])
    (HERE / 'usage_scan.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for mech, r in result.items():
        print(mech, 'dirs', r['dirs'], 'core_dirs', r['core_using_dir_count'], 'contracts', r['contracts'],
              'ops', r['ops'], 'types', r['symbol_types'], 'bases', r['bases'], 'outcomes', r['outcomes'],
              'py', r['py_files'], r['py_lines'], 'dedicated', r['dedicated_checker_count'], 'controls', r['control_dirs'])


def _records(obj):
    if isinstance(obj, dict):
        if 'sample_event' in obj and 'basis' in obj and 'facts' in obj:
            yield obj['basis']
        for v in obj.values():
            yield from _records(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _records(v)


def _outcomes(obj):
    if isinstance(obj, dict):
        if 'relation_at_observation' in obj and 'contract_id' in obj:
            yield obj['relation_at_observation']
        for v in obj.values():
            yield from _outcomes(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _outcomes(v)


if __name__ == '__main__':
    main()
