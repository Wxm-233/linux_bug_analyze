"""Compare preregistered finite relations; do not label detection accuracy."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent


def main():
    target = HERE / 'analysis.json'
    if target.exists():
        raise RuntimeError('preserve first analysis')
    protocol = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    execution = json.loads((HERE / 'execution.json').read_text(encoding='utf-8'))
    assert execution['status'] == 'all_preregistered_host_records_completed'
    observations = {(r['case'], r['version']): r['observation'] for r in execution['runs']}
    pairs, narrow = [], []
    for case in protocol['cases']:
        old = observations[(case['id'], 'parent')]
        fixed = observations[(case['id'], 'fixed')]
        assert old['nr_before'] == fixed['nr_before']
        for obs in [old, fixed]:
            assert obs['nr_after_provider'] == obs['nr_after_early'] == obs['nr_after_late']
            assert obs['provider_selected'] == int(case['mode'] == 'pv_domu')
            if obs['provider_selected']:
                assert obs['boot_registration_calls'] == 1
                assert obs['registration_attempts'] == obs['nr_after_early']
                assert obs['attempted_ids'] == list(range(obs['registration_attempts']))
                assert obs['smp_found_config'] == 1
            else:
                assert obs['registration_attempts'] == obs['boot_registration_calls'] == 0
        pair = {'case': case['id'], 'profile': case['profile'], 'mode': case['mode'],
                'parent_bound': old['nr_after_early'], 'fixed_bound': fixed['nr_after_early'],
                'parent_attempts': old['registration_attempts'], 'fixed_attempts': fixed['registration_attempts'],
                'parent_late_restrict': old['late_restrict_to_up'], 'fixed_late_restrict': fixed['late_restrict_to_up'],
                'parent_setter_calls': old['setter_calls'], 'fixed_setter_calls': fixed['setter_calls'],
                'parent_warns': old['setter_warn_count'], 'fixed_warns': fixed['setter_warn_count']}
        if case['mode'] == 'pv_domu' and case['profile'] in ['dynamic4', 'mpparse4']:
            expected = min(old['nr_before'], case['possible_cap'])
            if not case['setup_max_cpus'] or case['preexisting_apic_disabled']:
                expected = min(expected, 1)
            pair['manual_projected_target'] = expected
            pair['parent_relation_satisfied'] = old['nr_after_early'] == expected
            pair['fixed_relation_satisfied'] = fixed['nr_after_early'] == expected
            narrow.append(pair)
        pairs.append(pair)
    result = {'task': 'N2.21', 'status': 'finite_projection_analysis_complete',
              'pairs': pairs, 'condition_pairs': len(pairs), 'host_version_records': len(execution['runs']),
              'host_builds': len(execution['builds']), 'paid_model_requests': 0,
              'narrow_manual_relation': {'eligible_condition_pairs': len(narrow),
                                       'parent_mismatches': [p['case'] for p in narrow if not p['parent_relation_satisfied']],
                                       'fixed_mismatches': [p['case'] for p in narrow if not p['fixed_relation_satisfied']]},
              'early_bound_changed_pairs': [p['case'] for p in pairs if p['parent_bound'] != p['fixed_bound']],
              'late_exception_same_despite_changed_bound': [p['case'] for p in pairs if p['parent_bound'] != p['fixed_bound']
                                                          and p['parent_late_restrict'] == p['fixed_late_restrict'] == 0],
              'evidence_level': 'instrumented extracted-source host projection; manual relationship; no Kconfig or Xen runtime',
              'new_independent_positive': 0, 'new_independent_normal': 0, 'new_defects': 0}
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['status', 'condition_pairs', 'host_version_records',
                                           'early_bound_changed_pairs', 'narrow_manual_relation']}))


if __name__ == '__main__':
    main()
