"""Archive new reconstructed facts, exercise source/policy failure boundaries."""
from pathlib import Path
from collections import Counter
import copy
import json
import sys

import source_adapter as adapter

HERE = Path(__file__).resolve().parent
OUT = HERE / 'analysis_attempt2'

def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def load(path):
    return json.loads(path.read_bytes())

def need(value, reason):
    if not value:
        raise ValueError(reason)

def main():
    need(not (HERE / 'analysis_attempt2').exists(), 'preserve_previous_analysis_attempt')
    OUT.mkdir()
    rows, items, parsings, inputs = [], {}, {}, {}
    for profile in adapter.PROFILES:
        receipt = adapter.verify(profile)
        folder = HERE / 'preprocessing' / profile
        parsed = adapter.parse((folder / 'topology.i').read_text(), receipt['source_tree'])
        parsings[profile] = parsed
        projection = adapter.project(parsed, 'x86' if receipt['arch']=='x86_64' else 's390')
        need(projection['status'] == 'supported', (profile, projection['unknowns']))
        evidence = OUT / (profile + '_effective_source.json')
        save(evidence.name, {'profile': profile, 'revision': receipt['revision'], 'config_sha256': receipt['before_sha256']['config'],
                             'preprocessed_sha256': receipt['preprocessed_sha256'], 'definition_timeline': parsed['events'],
                             'use_snapshots': parsed['snapshots'], 'projection': projection,
                             'historical_runtime_source_origin': 'unknown', 'new_reconstruction_not_new_boot': True})
        item = adapter.envelope(profile, projection, evidence)
        items[profile] = item
        verdict = adapter.evaluate(item)
        rows.append({'profile': profile, 'id_native': projection['id_native'], 'mask_native': projection['mask_native'],
                     'compiled_die_attribute_count': projection['count'], 'final_macros_exist': all(parsed['pp']['macro_definitions'].get(n) for n in [adapter.ID_MACRO, adapter.MASK_MACRO]),
                     'policy_application': item['policy_application'], 'historical_normative_verdict': item['historical_normative_verdict'],
                     'effective_TU_reconstruction': verdict, 'historical_runtime_origin': 'unknown'})
        for name in ['receipt.json', 'command.json', 'compiler_version.txt', 'include_provenance.json', 'topology.i']:
            inputs[str((folder / name).relative_to(HERE))] = adapter.sha(folder / name)
        inputs[str(evidence.relative_to(HERE))] = adapter.sha(evidence)
    save('contract_inputs.json', {'rows': list(items.values()), 'core_sha256': adapter.sha(adapter.CORE),
                                  'semantic_requirement_origin': 'existing researcher-reviewed versioned policy',
                                  'automatic_semantic_extractions': 0})
    controls = []
    def exercise(name, item, expected='insufficient', category='synthetic evidence mutation'):
        verdict = adapter.evaluate(item)
        need(verdict['relation_at_observation'] == expected, (name, verdict))
        controls.append({'name': name, 'category': category, 'expected': expected, 'actual': verdict})
    item = copy.deepcopy(items['old_s390'])
    item['policy_application'] = item['ledger']['documents']['policy_application']['interpretation'] = 'repair_policy_application'
    exercise('repair_policy_cannot_be_claimed_historical_in_parent', item)
    item = copy.deepcopy(items['fixed_x86_64'])
    item['ledger']['source_policy_revision'] = adapter.legacy.OLD
    exercise('wrong_source_policy_revision', item)
    item = copy.deepcopy(items['fixed_x86_64'])
    item['record']['context_id'] = 'different.configuration'
    exercise('different_configuration_context', item)
    item = copy.deepcopy(items['fixed_s390'])
    item['record']['facts'].pop('native_id')
    item['ledger']['claims']['review.provider_binding']['status'] = 'unknown'
    exercise('no_export_does_not_short_circuit_unknown_origin', item)
    item = copy.deepcopy(items['old_s390'])
    item['historical_normative_verdict'] = 'violated'
    exercise('cannot_promote_counterfactual_to_old_ABI_violation', item)
    item = copy.deepcopy(items['fixed_x86_64'])
    item['record']['facts']['native_mask']['value'] = False
    exercise('fact_must_match_reviewed_projection', item)
    # These exercise projection semantics below the artifact hash gate. They
    # are explicitly constructed inputs, not re-preprocessed Linux variants.
    def projection_control(name, profile, mutate):
        parsed = copy.deepcopy(parsings[profile])
        mutate(parsed)
        projection = adapter.project(parsed, 'x86' if profile.endswith('x86_64') else 's390')
        need(projection['status'] == 'insufficient', (name, projection))
        item = adapter.envelope(profile, projection, OUT / (profile + '_effective_source.json'))
        exercise(name, item, category='constructed parsed-source control, not Linux execution')
        controls[-1]['projection_unknowns'] = projection['unknowns']
    projection_control('architecture_header_path_cannot_certify_forwarded_fallback', 'fixed_x86_64',
                       lambda p: p['pp']['macro_definitions'][adapter.ID_MACRO][0].update(definition=adapter.SHORT_BODIES['fallback_id']))
    projection_control('missing_effective_mask_origin', 'fixed_s390',
                       lambda p: p['pp']['macro_definitions'].update({adapter.MASK_MACRO: []}))
    projection_control('flag_defined_before_native_providers', 'fixed_x86_64',
                       lambda p: p['pp']['macro_definitions'][adapter.FLAG][0].update(preprocessed_line=1))
    projection_control('definition_changes_after_show_expansion', 'old_x86_64',
                       lambda p: p['snapshots']['id_expansion']['macro_state'][adapter.ID_MACRO].update(definition=adapter.SHORT_BODIES['fallback_id']))
    projection_control('effective_SMP_configuration_is_not_just_profile_name', 'fixed_x86_64',
                       lambda p: p['snapshots']['bin_table']['macro_state']['CONFIG_SMP'].update(definition='#define CONFIG_SMP 0'))
    projection_control('SYSFS_unknown_must_not_be_replaced_by_source_absence', 'fixed_s390',
                       lambda p: p['snapshots']['bin_table']['macro_state'].pop('CONFIG_SYSFS'))
    projection_control('only_one_member_of_group_is_not_full_export_evidence', 'old_s390',
                       lambda p: p['pp']['arrays']['bin_attrs'].update(text=p['pp']['arrays']['bin_attrs']['text'].replace('&bin_attr_die_cpus,', '')))
    # Reuse the six old static contexts and four old runtime contexts only as
    # archive replay. They are not new preprocessing, kernels or samples.
    previous = load(adapter.LEGACY / 'transfer_inputs.json')
    replay = []
    for old in previous['rows']:
        result = adapter.evaluate(old)
        replay.append({'profile': old['profile'], 'basis': old['record']['basis'], 'result': result})
    old_binding_path = HERE.parent / 'runtime_source_binding_20261020/binding_results.json'
    historical = load(old_binding_path)
    historical_rows = [{'profile': row['profile'], 'runtime_effective_native': row['runtime_effective_native'],
                         'run_relation_at_observation': row['run_relation_at_observation']} for row in historical['rows']]
    save('controls.json', {'controls': controls, 'count': len(controls), 'all_met_expected': True,
                           'not_independent_samples': True})
    save('archive_replay.json', {'rows': replay, 'historical_binding_unchanged': historical_rows,
                                 'historical_binding_sha256': adapter.sha(old_binding_path),
                                 'new_runtime_facts_injected': 0})
    result = {'rows': rows, 'relation_counts': dict(Counter(row['effective_TU_reconstruction']['relation_at_observation'] for row in rows)),
              'new_full_TU_preprocessing': 4, 'new_compilation': 0, 'new_boots': 0, 'new_model_calls': 0,
              'new_core_evaluations': len(rows) + len(controls), 'archive_core_replays': len(replay),
              'controls': len(controls), 'new_defects': 0, 'independent_positive_normal': [0, 0],
              'historical_runtime_origin_upgrades': 0, 'core_sha256': adapter.sha(adapter.CORE),
              'stage': 'effective source reconstruction and version-policy adapter; runtime/hardware truth remains open'}
    save('results.json', result)
    save('input_index.json', inputs)
    print(json.dumps({'rows': rows, 'new_core_evaluations': result['new_core_evaluations'],
                      'archive_core_replays': len(replay), 'controls': len(controls)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
