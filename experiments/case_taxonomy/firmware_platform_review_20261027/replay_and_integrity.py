"""Stage-review re-verification for the firmware/platform family (no new execution):
archive integrity, recount of archived summaries from per-case records, and core replay."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
CASES = HERE.parent
INNER = HERE.parents[2]
OUT = INNER / 'analysis_out'
sys.path.insert(0, str(INNER))
from linux_bug_analyze.contract_protocol import evaluate_contract  # noqa: E402

CORE_SHA = '42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def acpi_contract():
    root = OUT / 'acpi-contract-20260914-v2'
    summary = load(root / 'summary.json')
    recount, diff = {}, []
    for profile, want in summary.items():
        rows = load(root / profile / 'results.json')
        got = {'cases': len(rows),
               'acceptance_mismatches': sum(r['observed']['accepted'] != r['expected']['accepted'] for r in rows),
               'capability_mismatches': sum(r['observed']['support'] != r['expected']['support'] for r in rows),
               'fully_matching': sum(not r['errors'] for r in rows)}
        recount[profile] = got
        if got != want:
            diff.append({'profile': profile, 'archived': want, 'recount': got})
    return {'profiles': len(summary), 'recount': recount, 'differences': diff}


def acpi_kunit():
    root = OUT / 'acpi-kunit-20260914'
    out = {}
    for mode in ('before', 'after'):
        run = load(root / f'{mode}-run.json')
        failed = {}
        for row in run['runs']:
            boot = (root / row['log']).read_text(errors='replace')
            found = re.findall(r'^\s*(not ok|ok) \d+ (fixture_installed|actual_cpu_masks|actual_apic_membership)\b', boot, re.M)
            failed[row['scenario']] = sorted({n for s, n in found if s == 'not ok'})
        out[mode] = {'artifact_mismatch': [n for n, d in run['artifacts'].items() if sha(root / n) != d],
                     'failed_scenarios': {k: v for k, v in failed.items() if v}}
    expected = {2: ['actual_apic_membership', 'actual_cpu_masks'], 3: ['actual_apic_membership', 'actual_cpu_masks']}
    out['matches_recorded_pattern'] = out['before']['failed_scenarios'] == expected and not out['after']['failed_scenarios']
    return out


def acpi_env():
    root = CASES / 'acpi_env_classification_20261027'
    manifest = load(root / 'delivery_manifest.json')['files']
    bad = [k for k, v in manifest.items() if not (root / k).is_file() or sha(root / k) != v]
    stored = {f"acpi.env.qemu_{r['env']}.{k}": v for r in load(root / 'analysis/results.json')['rows']
              for k, v in r['decisions'].items()}
    mism, counts = [], Counter()
    for item in load(root / 'analysis/contract_inputs.json'):
        got = evaluate_contract(item['contract'], item['ledger'], item['record'])['relation_at_observation']
        counts[got] += 1
        if stored.get(item['contract']['id']) != got:
            mism.append(item['contract']['id'])
    return {'manifest_checked': len(manifest), 'manifest_mismatch': bad, 'replayed': sum(counts.values()),
            'decisions': dict(counts), 'replay_mismatch': mism}


def xen():
    root = CASES / 'cpu_stage_propagation_20261022'
    a = load(root / 'analysis.json')
    changed = sorted(p['case'] for p in a['pairs'] if p['parent_bound'] != p['fixed_bound'])
    late_same = sorted(p['case'] for p in a['pairs'] if p['parent_bound'] != p['fixed_bound']
                       and p['parent_late_restrict'] == p['fixed_late_restrict'])
    return {'pairs': len(a['pairs']), 'early_bound_changed_recount': changed,
            'archived_early_bound_changed': a['early_bound_changed_pairs'],
            'late_same_recount': late_same, 'archived_late_same': a['late_exception_same_despite_changed_bound'],
            'consistent': changed == sorted(a['early_bound_changed_pairs']) and late_same == sorted(a['late_exception_same_despite_changed_bound']),
            'file_sha': {n: sha(root / n) for n in ['README.md', 'analysis.json', 'results.json', 'execution.json']}}


def main():
    if sha(INNER / 'linux_bug_analyze/contract_protocol.py') != CORE_SHA:
        raise SystemExit('common core changed')
    target = HERE / 'replay_results.json'
    if target.exists():
        raise SystemExit('preserve replay_results.json')
    other = {n: {f: sha(CASES / n / f) for f in ['README.md', 'results.json'] if (CASES / n / f).is_file()}
             for n in ['cpu_domain_qualification_20261022', 'cpu_write_effects_20261023', 'firmware_platform_audit_20261027']}
    res = {'acpi_contract_v2': acpi_contract(), 'acpi_kunit': acpi_kunit(), 'acpi_env_classification': acpi_env(),
           'xen_stage_propagation': xen(), 'snapshots_without_manifest': other,
           'new_builds': 0, 'new_boots': 0, 'model_calls': 0}
    target.write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'acpi_contract_diff': res['acpi_contract_v2']['differences'],
                      'kunit_pattern': res['acpi_kunit']['matches_recorded_pattern'],
                      'kunit_artifact_mismatch': [len(res['acpi_kunit'][m]['artifact_mismatch']) for m in ('before', 'after')],
                      'env': {k: v for k, v in res['acpi_env_classification'].items() if k != 'manifest_mismatch'} | {'manifest_mismatch': len(res['acpi_env_classification']['manifest_mismatch'])},
                      'xen_consistent': res['xen_stage_propagation']['consistent']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
