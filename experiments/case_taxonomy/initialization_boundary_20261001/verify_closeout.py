"""Verify saved initialization evidence; no compiler, model or Git query.

The optional one-time freeze is after development, not an independent holdout.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RULES = HERE.parent
PRIOR = RULES / 'contract_authority_20261001'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def safe(relative):
    path = (RULES / relative).resolve()
    require(path.is_relative_to(RULES.resolve()), 'path escapes evidence root')
    return path


def check(records):
    for item in records:
        require(sha(safe(item['path'])) == item['sha256'], item['path'])
    return records


def save_once(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def previous():
    # The old verifier is normally executed from its own script directory.
    # Preserve that local import search path when loading it read-only here.
    sys.path.insert(0, str(PRIOR))
    spec = importlib.util.spec_from_file_location('previous_authority_closeout',
                                                PRIOR / 'verify_closeout.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify()


def verify(require_freeze=True):
    locked = check(read(HERE / 'freeze_manifest.json')['files']) if require_freeze else []
    old = previous()
    data = read(HERE / 'results.json')
    source = read(HERE / 'source_evidence.json')
    audit = read(HERE / 'source_review/harness_audit_final.json')
    design = read(HERE / 'check_design/audit_final.json')
    controls = read(HERE / 'check_design/strategy_controls.json')
    expected_path = HERE / 'source_review/expected_matrix_pre_harness.json'
    expected = read(expected_path)
    require(not audit['blockers_found'] and all(audit['checks'].values()), 'source audit')
    for filename, digest in audit['final_inputs_sha256'].items():
        require(sha(HERE / filename) == digest, 'final audited ' + filename)
    require(sha(expected_path) == audit['pre_harness_expected_matrix_sha256'], 'pre matrix')
    require(expected['saved_at_utc'] < data['created_utc'], 'pre matrix saved before final run')
    for key, filename in [('result_sha256', 'results.json'), ('runner_sha256', 'run_entry.py'),
                          ('source_evidence_sha256', 'source_evidence.json'),
                          ('source_expected_sha256', 'source_review/expected_matrix_pre_harness.json'),
                          ('design_sha256', 'check_design/README.md')]:
        require(design[key] == sha(HERE / filename), 'design audit ' + key)
    integrity = data['run_integrity']
    require(data['runner_sha256'] == integrity['runner_sha_before'] ==
            integrity['runner_sha_after'] == sha(HERE / 'run_entry.py'), 'runner identity')
    excerpts = {}
    for variant, evidence in source['variants'].items():
        c_path = HERE / ('entry_' + variant + '.c')
        require(sha(c_path) == data['generated_c_sha256'][variant] ==
                integrity['generated_sha_before'][variant] ==
                integrity['generated_sha_after'][variant] ==
                evidence['generated_c_sha256'], 'C identity ' + variant)
        c_text = c_path.read_text(encoding='utf-8')
        for item in evidence['excerpts']:
            # The fixture repeats the two historical scalar defaults with new
            # indentation; the four original functions remain literal text.
            preserved = (item['text'].strip() if item['label'].startswith('historical_default_')
                         else item['text'])
            require(c_text.count(preserved) == 1, 'preserved excerpt ' + item['label'])
            key = (variant, item['label'], item['revision'], item['path'],
                   item['start_line'], item['end_line'])
            require(key not in excerpts, 'duplicate excerpt binding')
            excerpts[key] = item
    require(len(excerpts) == len(audit['exact_preserved_source_excerpts']) == 92, 'excerpt count')
    for item in audit['exact_preserved_source_excerpts']:
        key = (item['variant'], item['label'], item['revision'], item['path'],
               item['start_line'], item['end_line'])
        evidence = excerpts[key]
        require(item['exact_git_excerpt_and_c_preservation'] and evidence['blob'] == item['blob']
                and hashlib.sha256(evidence['text'].encode()).hexdigest() == item['excerpt_sha256'],
                'source audit binding ' + item['label'])
    require(all(cmd['returncode'] == 0 for cmd in data['commands']), 'formal command exit')
    expected_rows = {(int(row['primary']), int(row['lmp_le_capable']),
                      int(row['data_len_feature']), int(row['init1_sync_error'])): row
                     for row in expected['rows']}
    require(len(expected_rows) == 16, 'source expected grid')
    groups = []
    for target, variants in data['targets'].items():
        order = {'x86_64': 'little', 's390x': 'big'}[target]
        for variant, result in variants.items():
            rows = result['rows']
            require(len(rows) == 16 and result['metadata']['actual_host_order'] == order,
                    'target metadata/grid')
            commands = [cmd for cmd in data['commands'] if 'stdout' in cmd and
                        cmd['argv'][-1].endswith('/' + target + '-' + variant) and
                        '-o' not in cmd['argv']]
            require(len(commands) == 1, 'one raw execution per group')
            raw = [json.loads(line) for line in commands[0]['stdout'].splitlines()]
            require(raw[0] == result['metadata'] and len(raw) == 17, 'raw metadata/count')
            seen, active, mismatch, inconsistent = set(), 0, 0, 0
            breakdown = dict(stage1_injected_error=0, amp_success=0, primary_success_dle_off=0)
            other_adds = 0
            for saved, row in zip(raw[1:], rows):
                require(all(row.get(key) == value for key, value in saved.items()), 'raw row binding')
                key = tuple(row[name] for name in ('primary', 'lmp_le_capability', 'extension', 'early_error'))
                require(key in expected_rows and key not in seen, 'unique expected row')
                seen.add(key)
                oracle = expected_rows[key]
                require(row['stages'] == oracle['expected_sync_call_stages'], 'source stages')
                require(row['result'] == (-5 if row['early_error'] else 0), 'source return')
                count = oracle['expected_target_add_attempts']
                require(row['target_add_attempt_count'] == row['simulated_target_copy_count'] ==
                        row['add_attempt_opcodes'].count(0x2024) == count, 'target attempt/copy')
                other_adds += len(row['add_attempt_opcodes']) - count
                require(row['host_values'] == [27, 328], 'fixed source values')
                if count:
                    active += 1
                    inconsistent += int(not row['lmp_le_capability'])
                    required = b''.join(value.to_bytes(2, 'little') for value in row['host_values'])
                    produced = b''.join(value.to_bytes(2, order if variant == 'parent' else 'little')
                                        for value in row['host_values'])
                    require(row['payload_hex'] == produced.hex() and
                            row['expected_schema_payload_hex'] == required.hex(), 'independent byte oracle')
                    decoded = [int.from_bytes(produced[i:i+2], 'little') for i in (0, 2)]
                    matches = produced == required
                    require(row['reader_values'] == decoded and
                            row['payload_matches_source_contract'] is matches and
                            row['local_reader_matches_host_values'] is matches,
                            'actual local reader versus byte oracle')
                    mismatch += int(not matches)
                else:
                    require(row['applicability'] == 'not_applicable' and
                            all(row[name] is None for name in ('payload_hex', 'expected_schema_payload_hex',
                                'payload_matches_source_contract', 'local_reader_matches_host_values')) and
                            row['reader_values'] == [51, 801], 'no byte verdict on unexecuted target')
                    reason = ('stage1_injected_error' if row['early_error'] else
                              'amp_success' if not row['primary'] else 'primary_success_dle_off')
                    breakdown[reason] += 1
            wanted = 2 if target == 's390x' and variant == 'parent' else 0
            require(active == 2 and inconsistent == 1 and mismatch == wanted, 'group totals')
            require(breakdown == dict(stage1_injected_error=8, amp_success=4, primary_success_dle_off=2)
                    and other_adds == 4, 'inactive/opcode controls')
            summary = result['summary']
            require(summary['configurations'] == 16 and summary['configurations_with_target_add_attempt'] == 2
                    and summary['not_applicable'] == 14 and summary['byte_mismatch_at_mock_copy'] == wanted,
                    'saved group summary')
            control = controls['controls'][target][variant]
            require(control['no_target_breakdown'] == breakdown and
                    control['zero_target_as_pass_would_make_unsupported_byte_claims'] == 14 and
                    control['ignore_opcode_would_count_unrelated_add_attempts'] == 4 and
                    control['actual_local_LE_mismatches'] == wanted, 'offline controls')
            group_audit = design['summaries'][target][variant]
            require(group_audit['target_add_attempts'] == 2 and group_audit['no_target_byte_verdict'] == 14
                    and group_audit['consistent_capability_activations'] ==
                    group_audit['inconsistent_capability_activations'] == 1
                    and group_audit['local_byte_mismatches'] == wanted, 'independent design audit')
            groups.append(dict(target=target, variant=variant, rows=16, target_add_attempts=active,
                               inconsistent_target_fixtures=inconsistent, no_target_byte_verdict=14,
                               byte_mismatches=mismatch))
    require(len(groups) == 4 and data['matrix']['total_cells'] == 64, 'four groups')
    return dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
                conclusion='Saved bounded source projection, independent audits and prior locks agree.',
                verified_new_files=locked, verified_prior_stage_files=old['verified_new_files'],
                verified_previous_generation_files=old['verified_prior_files'],
                verified_ancestry_entries=old['verified_ancestry_entries'],
                verified_old_raw_reports=old['verified_old_raw_reports'],
                groups=groups, source_evidence_excerpts=92,
                literal_c_excerpts=88, indentation_normalized_default_assignments=4,
                independent_new_cases=0, independent_holdout_executions=0,
                real_kernel_queue_execution=False, in_kernel_enforcement=False,
                limits='Mock copy; inconsistent capabilities and all physical reachability unproved; not generalization.')


def freeze():
    files = {path.resolve() for path in HERE.rglob('*') if path.is_file()
             and '__pycache__' not in path.parts
             and path.name not in ('freeze_manifest.json', 'completion_manifest.json')}
    files.update((PRIOR / name).resolve() for name in
                 ('freeze_manifest.json', 'completion_manifest.json', 'verify_closeout.py'))
    save_once(HERE / 'freeze_manifest.json',
              dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
                   scope='Post-development lock of known-case initialization boundary; no blind holdout.',
                   dependencies='Previous closeout verifier and manifests; its recorded dependencies checked recursively.',
                   historical_only=['check_design/audit.json', 'development_failures.json'],
                   files=[dict(path=path.relative_to(RULES).as_posix(), sha256=sha(path))
                          for path in sorted(files)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-unfrozen', action='store_true')
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--save-completion', action='store_true')
    args = parser.parse_args()
    require(not (args.check_unfrozen and (args.freeze or args.save_completion)), 'preflight is read-only')
    if args.freeze:
        verify(require_freeze=False)
        freeze()
    result = verify(require_freeze=not args.check_unfrozen)
    if args.save_completion:
        save_once(HERE / 'completion_manifest.json', result)
    print('verified:', len(result['verified_new_files']), 'stage records;',
          len(result['verified_prior_stage_files']), 'prior,',
          len(result['verified_previous_generation_files']), 'previous,',
          len(result['verified_ancestry_entries']), 'older;',
          '64 rows, 8 target attempts, 56 without byte verdict; independent new cases 0')


if __name__ == '__main__':
    main()
