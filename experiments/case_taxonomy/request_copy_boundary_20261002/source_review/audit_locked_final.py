"""Read-only audit of frozen source, harness, stdout and result artifacts.

Only writes this review directory; never imports or executes the experiment,
compiles C, launches an executable, or modifies its inputs.
"""
import datetime
import hashlib
import json
import pathlib
import re

REVIEW = pathlib.Path(__file__).resolve().parent
STAGE = REVIEW.parent
LOCK_PATH = REVIEW / 'input_lock_final.json'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def whole_function(text, name):
    starts = list(re.finditer(r'^(?:static\s+)?(?:inline\s+)?[^\n]+\b' + re.escape(name) + r'\([^;]*?\n\{', text, re.M))
    if len(starts) != 1:
        raise ValueError(f'{name}: expected one definition, saw {len(starts)}')
    start = starts[0].start()
    brace = text.index('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if not depth:
                return text[start:i+1]
    raise ValueError(f'{name}: unterminated definition')

lock = read_json(LOCK_PATH)
inputs = []
blockers = []
checks = []
def check(label, actual, expected):
    passed = actual == expected
    record = {'check': label, 'passed': passed, 'status': 'pass' if passed else 'fail', 'actual': actual, 'expected': expected}
    checks.append(record)
    if not passed:
        blockers.append(record)
    return passed

for name, expected_sha in lock['sha256'].items():
    path = STAGE / name
    raw = path.read_bytes()
    actual = digest(raw)
    inputs.append({'relative_path': name, 'sha256': actual, 'byte_count': len(raw), 'expected_sha256': expected_sha})
    check('input_lock:' + name, actual, expected_sha)
if blockers:
    raise SystemExit('Final input hashes do not match lock; refusing a final binding')

oracle_path = REVIEW / 'expected_matrix_pre_harness.json'
oracle = read_json(oracle_path)
receipt = read_json(REVIEW / 'oracle_seal_receipt.json')
manifest = read_json(REVIEW / 'source_manifest_pre_harness.json')
compiler_authority = read_json(REVIEW / 'post_compiler_authority/evidence.json')
result = read_json(STAGE / 'results.json')
source_evidence = read_json(STAGE / 'source_evidence.json')
oracle_sha = digest(oracle_path.read_bytes())
check('sealed_oracle_sha', oracle_sha, receipt['sha256'])
check('expected_conditions_count', len(oracle['conditions']), 4)
check('expected_variant_observations_count', oracle['variant_observations_count'], 16)
check('result_binding_to_oracle', result['pre_run_bindings']['independent_expected_pre'], oracle_sha)
check('result_binding_to_source_evidence', result['pre_run_bindings']['source_evidence'], lock['sha256']['source_evidence.json'])
check('result_binding_to_protocol', result['pre_run_bindings']['protocol_pre'], lock['sha256']['protocol_pre.md'])
check('bindings_before_after', result['run_integrity']['artifact_bindings_before'], result['run_integrity']['artifact_bindings_after'])
check('runner_before_hash', result['run_integrity']['runner_sha_before'], lock['sha256']['run_request_copy.py'])
check('runner_after_hash', result['run_integrity']['runner_sha_after'], lock['sha256']['run_request_copy.py'])
check('evidence_runner_hash', source_evidence['runner_sha256'], lock['sha256']['run_request_copy.py'])
check('oracle_precedes_result_creation', datetime.datetime.fromisoformat(oracle['sealed_at_utc']) < datetime.datetime.fromisoformat(result['created_utc']), True)

sources = {}
for source in manifest['files']:
    raw = (REVIEW / source['saved_relative_path']).read_bytes()
    check('independent_source_sha:' + source['saved_relative_path'], digest(raw), source['sha256'])
    git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    check('independent_source_blob:' + source['saved_relative_path'], git_blob, source['blob_sha1'])
    sources[(source['version'], source['source_path'])] = {'record': source, 'text': raw.decode('utf-8')}

preservation = []
for variant, record in source_evidence['variants'].items():
    source_version = 'fixed' if variant == 'fix' else 'parent'
    c_name = record['generated_c']
    c_raw = (STAGE / c_name).read_bytes()
    c_text = c_raw.decode('utf-8')
    c_sha = digest(c_raw)
    check('generated_c_evidence_hash:' + variant, c_sha, record['generated_c_sha256'])
    check('generated_c_before_hash:' + variant, result['run_integrity']['generated_c_sha_before'][variant], c_sha)
    check('generated_c_after_hash:' + variant, result['run_integrity']['generated_c_sha_after'][variant], c_sha)
    for source in record['source_files']:
        independent = sources[(source_version, source['path'])]['record']
        check('source_file_sha:' + variant + ':' + source['path'], source['source_sha256'], independent['sha256'])
        check('source_file_blob:' + variant + ':' + source['path'], source['git_blob'], independent['blob_sha1'])
        check('source_revision:' + variant + ':' + source['path'], source['revision'], independent['revision'])
    for ex in record['excerpts']:
        independent = sources[(source_version, ex['path'])]
        text = ex['text']
        check('excerpt_presence:' + variant + ':' + ex['label'], independent['text'].count(text), 1)
        check('excerpt_digest:' + variant + ':' + ex['label'], digest(text.encode('utf-8')), ex['excerpt_sha256'])
        actual_start = independent['text'][:independent['text'].index(text)].count('\n') + 1
        check('excerpt_start_line:' + variant + ':' + ex['label'], actual_start, ex['start_line'])
        check('excerpt_end_line:' + variant + ':' + ex['label'], actual_start + text.count('\n'), ex['end_line'])
        projected_excerpt = text.strip() if ex['label'].startswith('historical_default_') else text
        check('excerpt_in_generated_c:' + variant + ':' + ex['label'], c_text.count(projected_excerpt), 1)
    functions = {
        'hci_init4_req': 'net/bluetooth/hci_core.c',
        'hci_req_add': 'net/bluetooth/hci_request.c',
        'hci_req_add_ev': 'net/bluetooth/hci_request.c',
        'hci_prepare_cmd': 'net/bluetooth/hci_request.c',
        'skb_put_data': 'include/linux/skbuff.h',
    }
    for name, owner in functions.items():
        original = whole_function(sources[(source_version, owner)]['text'], name)
        projected = whole_function(c_text, name)
        check('complete_function_verbatim:' + variant + ':' + name, projected, original)
        preservation.append({'variant': variant, 'function': name, 'path': owner,
                             'original_text_sha256': digest(original.encode()), 'preserved_verbatim': projected == original})
    check('hci_req_add_not_macro:' + variant, bool(re.search(r'^#define\s+hci_req_add\b', c_text, re.M)), False)
    req_ex = next(x for x in record['excerpts'] if x['label'] == 'hci_request')
    check('request_struct_verbatim:' + variant, c_text.count(req_ex['text']), 1)
    check('explicit_cb_alignment:' + variant, 'unsigned char cb[64] __attribute__((aligned(8)))' in c_text, True)
    check('packed_header_assertions:' + variant, '_Static_assert(sizeof(struct hci_command_hdr)==3' in c_text and '_Static_assert(offsetof(struct hci_command_hdr,plen)==2' in c_text, True)
    check('payload_size_assertion:' + variant, '_Static_assert(sizeof(struct hci_cp_le_write_def_data_len)==4' in c_text, True)

source_checks = result['source_integrity_checks']
check('formal_source_recheck_count', len(source_checks), 14)
for source_check in source_checks:
    revision, path = source_check['argv'][2].split(':', 1)
    source_version = next(k for k, v in oracle['revisions'].items() if v == revision)
    check('formal_source_recheck:' + revision + ':' + path, source_check['stdout_sha256'], sources[(source_version, path)]['record']['sha256'])
    check('formal_source_command_return:' + revision + ':' + path, source_check['returncode'], 0)

compiler_records = []
for source in compiler_authority['files']:
    raw = (REVIEW / source['saved_relative_path']).read_bytes()
    check('post_compiler_authority_sha:' + source['version'], digest(raw), source['sha256'])
    check('post_compiler_option_authority:' + source['version'], any('-fno-strict-aliasing' in x['text'] for x in source['relevant_lines']), True)
for command in result['commands']:
    check('formal_command_return:' + ' '.join(command['argv']), command['returncode'], 0)
    if '-o' in command['argv']:
        check('compile_has_linux_aliasing_assumption:' + command['argv'][-1], '-fno-strict-aliasing' in command['argv'], True)
        compiler_records.append({'argv': command['argv'], 'returncode': command['returncode'], 'stderr': command['stderr']})
check('formal_compile_count', len(compiler_records), 4)

expected_by_key = {}
for condition in oracle['conditions']:
    for variant in condition['variants']:
        result_variant = 'fix' if variant['version'] == 'fixed' else 'parent'
        key = (result_variant, variant['architecture'], condition['initial_req_err'], condition['allocation_configured_outcome'])
        expected_by_key[key] = (condition, variant)

raw_records = []
row_comparisons = []
seen = set()
row_checks = []
raw_dir = REVIEW / 'raw_stdout_final'
raw_dir.mkdir(exist_ok=True)
for binary in result['temporary_executables']['records']:
    target, variant = binary['target'], binary['variant']
    execution = [x for x in result['commands'] if x['argv'][-1] == binary['temporary_path'] and '-o' not in x['argv']]
    check('raw_execution_unique:' + target + ':' + variant, len(execution), 1)
    command = execution[0]
    check('launcher:' + target + ':' + variant, command['argv'][:-1], ['qemu-s390x'] if target == 's390x' else [])
    stdout = command['stdout']
    raw = stdout.encode('utf-8')
    raw_name = f'{target}_{variant}.jsonl'
    (raw_dir / raw_name).write_bytes(raw)
    parsed = [json.loads(x) for x in stdout.splitlines()]
    item = result['targets'][target][variant]
    check('raw_lines:' + target + ':' + variant, len(parsed), 5)
    check('raw_meta_equals_result:' + target + ':' + variant, parsed[0], item['metadata'])
    check('observed_arch_order:' + target + ':' + variant, parsed[0]['actual_host_order'], 'big' if target == 's390x' else 'little')
    check('observed_payload_size:' + target + ':' + variant, parsed[0]['payload_size'], 4)
    check('observed_header_size:' + target + ':' + variant, parsed[0]['header_size'], 3)
    raw_records.append({'target': target, 'variant': variant, 'argv': command['argv'], 'stdout_sha256': digest(raw),
                        'stdout_byte_count': len(raw), 'saved_relative_path': 'raw_stdout_final/' + raw_name,
                        'returncode': command['returncode'], 'stderr': command['stderr'], 'binary_sha256_recorded': binary['sha256']})
    for raw_row in parsed[1:]:
        key = (variant, target, raw_row['req_err_initial'], raw_row['allocation_configuration'])
        check('matrix_key_unique:' + str(key), key in seen, False)
        seen.add(key)
        condition, exp_variant = expected_by_key[key]
        processed = next(x for x in item['rows'] if (x['req_err_initial'], x['allocation_configuration']) == key[2:])
        check('raw_row_equals_result_base:' + str(key), {k: processed[k] for k in raw_row}, raw_row)
        copied = condition['payload_memcpy_performed']
        allocation_failure = condition['allocator_actually_called'] and condition['allocation_configured_outcome'] == 'failure'
        expectations = {
            'variant': variant,
            'init4_return_value': condition['init4_return'],
            'req_err_after': condition['final_req_err'],
            'primary': True, 'lmp_le_capability': True, 'data_length_extension': True,
            'host_values': [27, 328], 'target_opcode': 0x2024, 'attempt_plen': 4,
            'add_attempt_count': condition['target_add_call_attempts'],
            'allocation_call_count': condition['allocator_call_count'],
            'allocation_failure_count': int(allocation_failure),
            'header_reservation_count': int(condition['header_storage_created']),
            'payload_reservation_count': condition['skb_put_data_call_count'],
            'payload_copy_completed_count': condition['payload_memcpy_count'],
            'queue_mock_enqueue_count': condition['queue_tail_observation_count'],
            'mock_queue_length': condition['queue_tail_observation_count'],
            'error_log_count': int(allocation_failure), 'helper_stub_calls': 1,
            'all_add_attempt_opcodes': [0x2024],
            'copy_header_hex': condition['header_hex'], 'copy_payload_hex': exp_variant['copied_payload_hex'],
            'copy_command_hex': exp_variant['queued_stub_packet_hex'],
            'queue_mock_header_hex': condition['header_hex'], 'queue_mock_payload_hex': exp_variant['copied_payload_hex'],
            'queue_mock_command_hex': exp_variant['queued_stub_packet_hex'],
            'queued_length': 7 if copied else 0, 'queued_packet_type': 1 if copied else 0,
            'queued_opcode': 0x2024 if copied else 0, 'queued_req_flags': 1 if copied else 0,
            'queued_req_event': 0, 'req_run_executed': False,
        }
        row_pass = True
        fields = []
        for name, expected in expectations.items():
            passed = check('row:' + processed['row_id'] + ':' + name, raw_row[name], expected)
            row_pass &= passed
            fields.append({'field': name, 'actual': raw_row[name], 'expected': expected, 'status': 'pass' if passed else 'fail'})
        normalized_format = 'not_evaluated' if not copied else ('matches_expected_little_endian' if raw_row['copy_payload_hex'] == '1b004801' else 'wrong_endian')
        row_pass &= check('normalized_format:' + processed['row_id'], normalized_format, exp_variant['copied_payload_format_status'])
        decoded = None
        if copied:
            payload = bytes.fromhex(raw_row['copy_payload_hex'])
            decoded = [int.from_bytes(payload[0:2], 'little'), int.from_bytes(payload[2:4], 'little')]
        row_pass &= check('decoded_payload:' + processed['row_id'], decoded, exp_variant['copied_payload_little_endian_values'])
        derived_expectations = {
            'byte_check_execution': 'executed_on_completed_copy' if copied else 'not_executed',
            'byte_verdict': ('conditional_numeric_match' if normalized_format == 'matches_expected_little_endian' else 'conditional_representation_mismatch') if copied else None,
            'header_matches_source_contract': True if copied else None,
            'payload_matches_source_contract': normalized_format == 'matches_expected_little_endian' if copied else None,
            'source_expected_payload_hex': '1b004801' if copied else None,
            'rejection_boundary': 'req.err guard' if condition['initial_req_err'] else ('allocator failure' if allocation_failure else None),
        }
        for name, expected in derived_expectations.items():
            row_pass &= check('derived:' + processed['row_id'] + ':' + name, processed[name], expected)
        row_comparisons.append({'row_id': processed['row_id'], 'condition_id': condition['condition_id'], 'status': 'pass' if row_pass else 'fail',
                                'normalized_copied_payload_format_status': normalized_format, 'decoded_little_endian_payload': decoded,
                                'fields': fields, 'derived_expectations': derived_expectations})

check('all_16_matrix_keys', seen, set(expected_by_key))
summary = {
    'total_rows': len(row_comparisons),
    'oracle_matched_rows': sum(x['status'] == 'pass' for x in row_comparisons),
    'add_attempt_rows': 16,
    'allocation_call_rows': sum(x['allocator_call_count'] for x in oracle['conditions']) * 4,
    'payload_copy_rows': sum(x['payload_memcpy_count'] for x in oracle['conditions']) * 4,
    'queue_mock_rows': sum(x['queue_tail_observation_count'] for x in oracle['conditions']) * 4,
    'not_evaluated_rows': sum(x['normalized_copied_payload_format_status'] == 'not_evaluated' for x in row_comparisons),
    'expected_representation_mismatch_rows': sum(x['normalized_copied_payload_format_status'] == 'wrong_endian' for x in row_comparisons),
}
for name, expected in [('total_rows',16), ('add_attempt_rows',16), ('allocation_call_rows',8), ('payload_copy_rows',4), ('queue_mock_rows',4), ('null_byte_verdict_rows',12), ('payload_mismatch_rows',1)]:
    check('runner_summary:' + name, result['summary'][name], expected)
for source in inputs:
    check('input_unchanged_after_audit:' + source['relative_path'], digest((STAGE / source['relative_path']).read_bytes()), source['sha256'])

# JSON requires deterministic lists rather than sets; long verbatim function
# values add no review value after their digest/preservation checks.
for record in checks:
    for name in ('actual', 'expected'):
        value = record[name]
        if isinstance(value, set):
            record[name] = sorted(list(value))
        elif isinstance(value, str) and '\n' in value and len(value) > 500:
            record[name] = {'sha256': digest(value.encode()), 'character_count': len(value)}

report = {
    'schema': 'independent-request-copy-final-audit-v1',
    'audited_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'pass_with_explicit_fixture_limits' if not blockers else 'fail',
    'blockers': blockers, 'blockers_found': blockers,
    'audit_only_no_compile_no_replay': True,
    'expected_sha256': oracle_sha, 'pre_harness_expected_sha256': oracle_sha,
    'expected_sealed_at_utc': oracle['sealed_at_utc'],
    'final_inputs_sha256': {x['relative_path']: x['sha256'] for x in inputs},
    'inputs': inputs, 'raw_stdout_inputs': raw_records,
    'compiler_command_records': compiler_records,
    'summary': summary, 'original_function_preservation': preservation,
    'request_struct': {'source_text_verbatim': True, 'full_kernel_layout_executed': False,
                       'qualification': 'Original hci_request declaration is preserved; sk_buff_head member type is a reduced queue fixture.'},
    'observation_boundaries': [
        'add attempts are observed at unchanged original add_ev BT_DBG before req.err guard; allocation count is separately recorded in allocator stub',
        'payload reservation is separately counted at skb_put; original skb_put_data memcpy performs payload byte copy',
        'copy completion is observed by original prepare BT_DBG after skb_put_data returns, not a counter instrumented inside memcpy itself',
        'post-copy snapshots read contiguous SKB fixture storage; queue_tail snapshots corroborate the same header/payload/command bytes',
        'hci_prepare_cmd calls, skb_put_data call count and queue-empty branch follow preserved source path; no separate call/queue-empty counter exists',
        'zero queue metadata fields on no-copy rows are output placeholders; byte arrays/verdicts are null and normalize to not_evaluated',
        'init4_return_value=0 is a real function return in all rows; req_err_after separately retains -EIO or stores -ENOMEM',
        'allocator command length 7 is checked by a fixture assertion; real alloc_skb reserves BT_SKB_RESERVE and is not executed',
    ],
    'limits': [
        'Direct original init4 invocation with fixed primary/LMP_LE/DLE and historical 27/328; no full initialization or feature-discovery execution',
        'Allocator, skb_put storage, minimal hci_dev/bt_skb_cb and queue implementations remain local fixtures',
        'Final compilation includes -fno-strict-aliasing, supported by both original Makefiles KBUILD_CFLAGS:459; the fixture is not a general ISO C object-model proof',
        'Packed command header needs alignment1; fixture cb is explicitly aligned8 for reduced byte/u16 metadata, but runtime pointer alignment is not independently instrumented',
        'Original bt_cb macro covers reduced declared character storage; real bt_skb_cb union/layout is not reproduced',
        'QEMU s390x user-mode process demonstrates observed big endian representation under the cross compiler, not hardware/controller execution',
        'No req_run, locking/workqueue, synchronous chain, response completion reader, transport or controller acceptance is exercised',
        'This is the already inspected historical development case; no new defect, independent holdout, hardware reachability proof or detector accuracy estimate',
        'Earlier compiler-flags results are development history; this audit binds only the explicitly locked final input hashes',
    ],
    'post_harness_compiler_authority': compiler_authority,
    'row_comparisons': row_comparisons,
    'checks': {x['check']: x['passed'] for x in checks},
    'detailed_check_records': checks,
}
(REVIEW / 'final_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'summary': summary, 'blockers_count': len(blockers), 'checks_count': len(checks)}))
