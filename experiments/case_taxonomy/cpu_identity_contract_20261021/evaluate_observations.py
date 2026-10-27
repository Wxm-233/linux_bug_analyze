"""Evaluate the predeclared relations; do not infer real-kernel legality."""
from pathlib import Path
import collections
import hashlib
import json

HERE = Path(__file__).resolve().parent


def bits(value):
    assert isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 256
    return {i for i in range(8) if value & (1 << i)}


def main():
    plan = json.loads((HERE / 'experiment_pre.json').read_bytes())
    execution = json.loads((HERE / 'execution.json').read_bytes())
    assert execution['status'] == 'twelve_source_projection_runs_complete'
    assert len(execution['runs']) == len(plan['runs']) == 12
    rows = []
    for declared, run in zip(plan['runs'], execution['runs']):
        assert all(run[k] == v for k, v in declared.items())
        observation = run['observation']
        assert run['returncode'] == 0
        assert observation['NR_CPUS'] == 8 and observation['BITS_PER_LONG'] == 64
        firmware = set(declared['firmware_order']) | {0}
        possible = bits(observation['pre_possible'])
        present = bits(observation['present'])
        assert present == firmware
        assert observation['pre_possible'] == observation['post_possible']
        assert observation['pre_nr_cpu_ids'] == declared['selection_limit']
        assert observation['post_nr_cpu_ids'] == max(possible) + 1
        assert observation['probed'] == len(declared['firmware_order'])
        limit = declared['selection_limit']
        no_invented = possible <= firmware
        count_ok = len(possible) == min(len(firmware), limit)
        unrestricted = len(firmware) <= limit
        retained = possible == firmware if unrestricted else None
        verdict = 'satisfy' if no_invented and count_ok and retained is not False else 'violate'
        all_present = present <= possible
        combined = {}
        for phase in ['pre', 'post']:
            bound = max(present) < observation[phase + '_nr_cpu_ids']
            combined[phase] = {'present_subset_possible': all_present,
                               'boot0_in_possible': 0 in possible,
                               'max_present_below_current_nr_cpu_ids': bound,
                               'combined': all_present and 0 in possible and bound}
        rows.append(dict(declared, provided=sorted(firmware), possible=sorted(possible),
                         present=sorted(present), pre_nr_cpu_ids=observation['pre_nr_cpu_ids'],
                         post_nr_cpu_ids=observation['post_nr_cpu_ids'],
                         properties={'no_invented_ids': no_invented, 'limited_count': count_ok,
                                     'identity_when_unrestricted': retained},
                         contract_verdict=verdict, original_model_predicates=combined,
                         diagnostic_first_L_only=(sorted(possible) == declared['firmware_order'][:limit]),
                         evidence_level='conditional source projection, not actual kernel contract verdict'))
    by_version = {version: dict(collections.Counter(row['contract_verdict'] for row in rows
                                                   if row['version'] == version))
                  for version in ['parent', 'fixed']}
    expected = plan['expected_before_execution']
    assert by_version['parent'].get('satisfy', 0) == expected['parent_contract']['satisfy']
    assert by_version['parent'].get('violate', 0) == expected['parent_contract']['violate']
    assert by_version['fixed'].get('satisfy', 0) == expected['fixed_contract']['satisfy']
    assert by_version['fixed'].get('violate', 0) == expected['fixed_contract']['violate']
    model_summary = {}
    for phase in ['pre', 'post']:
        count_true = sum(row['original_model_predicates'][phase]['combined'] for row in rows
                         if row['version'] == 'fixed')
        model_summary[phase] = {'true': count_true, 'false': 6 - count_true}
        assert model_summary[phase] == expected['fixed_original_combined_' + ('before' if phase == 'pre' else 'after')]
    renaming = []
    rename = {0: 0, 1: 2}
    for version in ['parent', 'fixed']:
        for limit in [2, 8]:
            dense = next(row for row in rows if row['version'] == version and
                         row['selection_limit'] == limit and row['input_id'] == 'dense_01')
            sparse = next(row for row in rows if row['version'] == version and
                          row['selection_limit'] == limit and row['input_id'] == 'reported_ids_02')
            renamed = sorted(rename[i] for i in dense['possible'])
            renaming.append({'version': version, 'limit': limit,
                             'renamed_dense_output': renamed, 'sparse_output': sparse['possible'],
                             'relation_holds': renamed == sparse['possible'],
                             'unit': 'relation on reused observations, not new sample/execution'})
    result = {'task': 'N2.18', 'status': 'predeclared_source_projection_evaluated', 'rows': rows,
              'contract_by_version': by_version, 'fixed_original_model_combined': model_summary,
              'renaming_relations': renaming,
              'count_only_passes': {v: sum(r['properties']['limited_count'] for r in rows if r['version'] == v)
                                    for v in ['parent', 'fixed']},
              'execution_sha256': hashlib.sha256((HERE / 'execution.json').read_bytes()).hexdigest(),
              'source_semantics_only': True, 'whole_kernel_contract_proved': False,
              'independent_cases': 0, 'new_bug_discoveries': 0,
              'automatic_contract_extraction': False,
              'unsupported': ['large/dynamic mask branch', 'actual legal SPARC configuration',
                              'paging-to-OF call chain', 'real boot/online/concurrency/allocations']}
    with (HERE / 'results.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'contract_by_version': by_version,
                      'fixed_original_model_combined': model_summary,
                      'count_only_passes': result['count_only_passes']}))


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, KeyError, ValueError) as error:
        with (HERE / 'evaluation_failure.json').open('x', encoding='utf-8') as f:
            json.dump({'status': 'evaluation_or_expectation_mismatch_preserved',
                       'error_type': type(error).__name__, 'error': str(error),
                       'execution_preserved': (HERE / 'execution.json').exists(),
                       'no_rerun_or_sample_exclusion': True}, f, indent=2)
            f.write('\n')
        raise
