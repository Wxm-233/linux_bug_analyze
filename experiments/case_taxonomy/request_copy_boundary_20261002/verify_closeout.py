"""Read-only checks of final saved request-copy evidence and prior locks.

No compiler, Git query, device or model is called. Freeze is post-development.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES = HERE.parent
PRIOR = RULES / 'initialization_boundary_20261001'
PRIOR_LOCKS = {
    'freeze_manifest.json': '3341ab479b64135bc8839887154335853d4c4b041ddcac196503cf5550f49d23',
    'completion_manifest.json': '1f87cb95855cd011214c8064fbced9492ff11746b7f2ada2e859e307d72dade7',
}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(relative):
    path = (RULES / relative).resolve()
    require(path.is_relative_to(RULES.resolve()), 'path escapes case_taxonomy')
    return path


def check(records):
    for item in records:
        require(sha(safe(item['path'])) == item['sha256'], item['path'])
    return records


def save_once(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify(require_freeze=True):
    locked = check(read(HERE / 'freeze_manifest.json')['files']) if require_freeze else []
    for filename, digest in PRIOR_LOCKS.items():
        require(sha(PRIOR / filename) == digest, 'prior anchor ' + filename)
    prior = read(PRIOR / 'completion_manifest.json')
    old = {}
    for name in ('verified_new_files', 'verified_prior_stage_files',
                 'verified_previous_generation_files', 'verified_ancestry_entries', 'verified_old_raw_reports'):
        old[name] = check(prior[name])
    require([len(old[name]) for name in old] == [32, 46, 55, 27, 4], 'prior record counts')
    require(old['verified_new_files'] == read(PRIOR / 'freeze_manifest.json')['files'], 'prior completion binding')
    result = read(HERE / 'results.json')
    source = read(HERE / 'source_evidence.json')
    expected_path = HERE / 'source_review/expected_matrix_pre_harness.json'
    expected = read(expected_path)
    audit = read(HERE / 'source_review/final_audit.json')
    require(not audit['blockers_found'] and all(audit['checks'].values()), 'independent final audit')
    for filename, digest in audit['final_inputs_sha256'].items():
        path = (HERE / filename).resolve()
        require(path.is_relative_to(HERE.resolve()) and sha(path) == digest, 'audited input ' + filename)
    require(sha(expected_path) == audit['pre_harness_expected_sha256'], 'independent oracle binding')
    require(expected['sealed_at_utc'] < result['created_utc'], 'oracle precedes final execution')
    require(expected['conditions_count'] == 4 and expected['variant_observations_count'] == 16,
            'source expectation size')
    integrity = result['run_integrity']
    require(integrity['runner_sha_before'] == integrity['runner_sha_after'] ==
            source['runner_sha256'] == sha(HERE / 'run_request_copy.py'), 'runner identity')
    artifacts = {'source_evidence': HERE / 'source_evidence.json',
                 'protocol_pre': HERE / 'protocol_pre.md', 'independent_expected_pre': expected_path}
    for key, path in artifacts.items():
        require(sha(path) == integrity['artifact_bindings_before'][key] ==
                integrity['artifact_bindings_after'][key] == result['pre_run_bindings'][key],
                'pre/post binding ' + key)
    manifest = read(HERE / 'source_review/source_manifest_pre_harness.json')
    raw_sources = {}
    for item in manifest['files']:
        raw = (HERE / 'source_review' / item['saved_relative_path']).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == item['sha256'] and
                hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['blob_sha1'],
                'raw source/blob ' + item['source_path'])
        raw_sources[(item['version'], item['source_path'])] = (item, raw.decode('utf-8'))
    require(len(raw_sources) == 26, 'full source bindings')
    excerpt_count, normalized = 0, 0
    for variant, evidence in source['variants'].items():
        c_path = HERE / evidence['generated_c']
        require(sha(c_path) == evidence['generated_c_sha256'] ==
                integrity['generated_c_sha_before'][variant] ==
                integrity['generated_c_sha_after'][variant], 'C identity ' + variant)
        c = c_path.read_text(encoding='utf-8')
        for item in evidence['excerpts']:
            metadata, original = raw_sources[('fixed' if variant == 'fix' else variant, item['path'])]
            require(item['revision'] == metadata['revision'] and item['git_blob'] == metadata['blob_sha1']
                    and item['source_sha256'] == metadata['sha256'], 'excerpt source identity')
            text = '\n'.join(original.splitlines()[item['start_line']-1:item['end_line']])
            require(text == item['text'] and hashlib.sha256(text.encode()).hexdigest() == item['excerpt_sha256'],
                    'exact raw excerpt ' + item['label'])
            default = item['label'].startswith('historical_default_')
            require(c.count(text.strip() if default else text) == 1, 'C preservation ' + item['label'])
            excerpt_count += 1
            normalized += int(default)
    require((excerpt_count, normalized) == (60, 4), 'excerpt preservation count')
    commands = result['commands']
    require(all(cmd['returncode'] == 0 for cmd in commands), 'formal command returns')
    compiles = [cmd for cmd in commands if '-o' in cmd['argv']]
    require(len(compiles) == 4 and all('-fno-strict-aliasing' in cmd['argv'] for cmd in compiles),
            'all formal compiler options')
    conditions = {(item['initial_req_err'], item['allocation_configured_outcome']): item
                  for item in expected['conditions']}
    totals = dict(total_rows=0, add_attempt_rows=0, allocation_call_rows=0, payload_copy_rows=0,
                  queue_mock_rows=0, null_byte_verdict_rows=0, payload_mismatch_rows=0)
    groups, controls = [], []
    for target, variants in result['targets'].items():
        order = {'x86_64': 'little', 's390x': 'big'}[target]
        for variant, group in variants.items():
            require(group['metadata']['actual_host_order'] == order and len(group['rows']) == 4,
                    'group metadata')
            runs = [cmd for cmd in commands if cmd['argv'][-1].endswith('/' + target + '-' + variant)
                    and '-o' not in cmd['argv']]
            require(len(runs) == 1, 'one final execution per group')
            raw = [json.loads(line) for line in runs[0]['stdout'].splitlines()]
            require(len(raw) == 5 and raw[0] == group['metadata'], 'raw stdout metadata')
            seen, copied, errors, mismatches = set(), 0, 0, 0
            for raw_row, row in zip(raw[1:], group['rows']):
                require(all(row.get(key) == value for key, value in raw_row.items()), 'raw row binding')
                key = (row['req_err_initial'], row['allocation_configuration'])
                require(key not in seen and key in conditions, 'unique condition')
                seen.add(key)
                oracle = conditions[key]
                active = oracle['payload_memcpy_performed']
                require(row['init4_return_value'] == oracle['init4_return'] == 0 and
                        row['req_err_after'] == oracle['final_req_err'], 'separate error channels')
                require(row['add_attempt_count'] == oracle['target_add_call_attempts'] == 1 and
                        row['all_add_attempt_opcodes'] == [0x2024] and row['attempt_plen'] == 4,
                        'target add attempt')
                require(row['allocation_call_count'] == oracle['allocator_call_count'] and
                        row['allocation_failure_count'] == int(not row['req_err_initial'] and
                                                               row['allocation_configuration'] == 'failure'),
                        'actual allocator versus configured outcome')
                require(row['payload_copy_completed_count'] == oracle['payload_memcpy_count'] and
                        row['payload_reservation_count'] == oracle['skb_put_data_call_count'] and
                        row['header_reservation_count'] == int(active) and
                        row['queue_mock_enqueue_count'] == oracle['queue_tail_observation_count'] and
                        row['mock_queue_length'] == int(active), 'copy/queue observations')
                require(row['req_run_executed'] is False and row['host_values'] == [27, 328], 'scope')
                require(row['primary'] and row['lmp_le_capability'] and row['data_length_extension'],
                        'fixed noncontradictory capabilities')
                if active:
                    copied += 1
                    required = b''.join(value.to_bytes(2, 'little') for value in row['host_values'])
                    produced = b''.join(value.to_bytes(2, order if variant == 'parent' else 'little')
                                        for value in row['host_values'])
                    matches = produced == required
                    require(row['copy_header_hex'] == row['queue_mock_header_hex'] == '242004' and
                            row['copy_payload_hex'] == row['queue_mock_payload_hex'] == produced.hex() and
                            row['copy_command_hex'] == row['queue_mock_command_hex'] == '242004' + produced.hex(),
                            'independent header and payload byte oracle')
                    require(row['source_expected_payload_hex'] == required.hex() and
                            row['header_matches_source_contract'] is True and
                            row['payload_matches_source_contract'] is matches and row['queued_length'] == 7 and
                            row['queued_req_event'] == 0 and row['queued_req_flags'] == 1,
                            'copied schema and queue metadata')
                    require(row['byte_check_execution'] == 'executed_on_completed_copy', 'copy check state')
                    mismatches += int(not matches)
                else:
                    require(all(row[name] is None for name in (
                        'copy_header_hex', 'copy_payload_hex', 'copy_command_hex', 'queue_mock_header_hex',
                        'queue_mock_payload_hex', 'queue_mock_command_hex', 'source_expected_payload_hex',
                        'header_matches_source_contract', 'payload_matches_source_contract', 'byte_verdict')),
                        'no format verdict without copy')
                    require(row['byte_check_execution'] == 'not_executed', 'no-copy check state')
                    errors += 1
                totals['total_rows'] += 1
                totals['add_attempt_rows'] += row['add_attempt_count']
                totals['allocation_call_rows'] += row['allocation_call_count']
                totals['payload_copy_rows'] += int(active)
                totals['queue_mock_rows'] += row['queue_mock_enqueue_count']
                totals['null_byte_verdict_rows'] += int(not active)
                totals['payload_mismatch_rows'] += int(active and not row['payload_matches_source_contract'])
            wanted = int(target == 's390x' and variant == 'parent')
            require(copied == 1 and errors == 3 and mismatches == wanted, 'group totals')
            groups.append(dict(target=target, variant=variant, rows=4, copied=1, not_copied=3, mismatch=wanted))
            controls.append(dict(target=target, variant=variant,
                init4_zero_return_without_copy=3,
                allocator_configured_failure_but_not_called=1,
                matching_header_with_mismatching_payload=wanted))
    require(len(groups) == 4 and totals == result['summary'] and totals['total_rows'] == 16,
            'saved overall summary')
    return dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
        conclusion='Final saved source-copy projection and independent audit agree; known development case only.',
        verified_new_files=locked, prior_record_groups=old,
        full_source_files=26, literal_c_excerpts=56, indentation_normalized_default_assignments=4,
        groups=groups, summary=totals, offline_strategy_observations=controls,
        independent_holdout_executions=0, new_confirmed_cases=0, in_kernel_enforcement=False,
        real_kernel_queue_execution=False, req_run_execution=False,
        audit_file_sha256=sha(HERE / 'source_review/final_audit.json'),
        limits='GNU/kernel compilation assumptions and skb/queue substitutes; no device or generalization proof.')


def freeze():
    files = {path.resolve() for path in HERE.rglob('*') if path.is_file()
             and '__pycache__' not in path.parts
             and path.name not in ('freeze_manifest.json', 'completion_manifest.json')}
    files.update((PRIOR / name).resolve() for name in PRIOR_LOCKS)
    save_once(HERE / 'freeze_manifest.json', dict(
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Post-development known-case request-copy lock; not an independent holdout.',
        dependencies='Prior anchor manifests record all recursively checked evidence.',
        historical_only=['development_previous_flags/', 'development_failures.json'],
        files=[dict(path=path.relative_to(RULES).as_posix(), sha256=sha(path)) for path in sorted(files)]))


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
    print('verified:', len(result['verified_new_files']), 'stage records; 32/46/55/27 prior records, 4 old raw;',
          '16 rows, 4 copies, 12 no-copy, 1 conditional mismatch; new confirmed cases 0')


if __name__ == '__main__':
    main()
