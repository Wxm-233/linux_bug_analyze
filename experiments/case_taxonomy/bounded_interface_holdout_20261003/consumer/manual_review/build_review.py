"""Build manual post-unseal inventory from locked raw/source evidence only."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


base_manifest = load(STAGE / 'source_manifest.json')
extra_manifest = load(HERE / 'source_manifest_extra.json')
manifests = base_manifest + extra_manifest
REVISIONS = {'parent': 'fac04efc5c793dccbd07e2d59af9f90b7fc0dca4',
             'fixed': '6d44a780635b9b3fb6e20f366ee7750a9adfa884'}
for entry in manifests:
    if entry['revision'] not in REVISIONS.values():
        continue
    data = (STAGE / entry['saved_path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256']
    assert hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest() == entry['blob_sha1']
assert len(extra_manifest) == 8
assert all(sum(item['revision'] == revision for item in extra_manifest) == 4 for revision in REVISIONS.values())


def quote(label, path, start, end=None, expected=None):
    revision = REVISIONS[label]
    entry = next(row for row in manifests if row['revision'] == revision and row['source_path'] == path)
    saved = STAGE / entry['saved_path']
    lines = saved.read_text(encoding='utf-8').splitlines()
    text = '\n'.join(lines[start-1:(end or start)])
    if expected is not None:
        assert expected in text, (path, start, expected)
    return {'revision': revision, 'source_path': path, 'saved_path': entry['saved_path'],
            'start_line': start, 'end_line': end or start, 'text': text,
            'sha256': entry['sha256'], 'blob_sha1': entry['blob_sha1']}


def both(path, start, end=None, expected=None):
    return [quote(label, path, start, end, expected) for label in REVISIONS]


quotes = {
    'target_parent': [quote('parent', 'fs/smb/client/reparse.c', 650, 688, 'symname_utf16, symname_utf8_len * 2')],
    'target_fixed': [quote('fixed', 'fs/smb/client/reparse.c', 650, 688, '(wchar_t *) symname_utf16')],
    'nls_declaration': both('include/linux/nls.h', 18, 19, 'typedef u16 wchar_t;') +
                       both('include/linux/nls.h', 40, 58, 'wchar_t *pwcs'),
    'nls_format_implementation': both('fs/nls/nls_base.c', 117, 133, '__cpu_to_le16(c)') +
                                 both('fs/nls/nls_base.c', 139, 170, 'put_utf16(op++'),
    'wsl_input_declaration': both('fs/smb/common/smb2pdu.h', 1555, 1562, 'Variable Length UTF-8 string without nul-term'),
    'local_input_and_dispatch': both('fs/smb/client/reparse.c', 699, 717, 'IO_REPARSE_TAG_LX_SYMLINK') +
                                both('fs/smb/client/reparse.c', 736, 748, 'rsp_iov->iov_base'),
    'ops_binding': both('fs/smb/client/smb2ops.c', 5273, 5273, '.parse_reparse_point = smb2_parse_reparse_point'),
    'utf16_consumer': both('fs/smb/client/cifs_unicode.c', 334, 364, 'cifs_from_utf16(dst, (__le16 *) src') +
                       both('fs/smb/client/cifs_unicode.c', 155, 204, 'get_unaligned_le16(&from[i])'),
    'reported_sizeof_posix': both('fs/smb/client/reparse.c', 483, 493, 'sizeof(buf->InodeType)') +
                              both('fs/smb/client/cifspdu.h', 1508, 1515, 'InodeType'),
    'reported_sizeof_wsl': both('fs/smb/client/reparse.c', 654, 665, 'sizeof(buf->Flags)') +
                            both('fs/smb/common/smb2pdu.h', 1555, 1562, '__le32'),
    'reported_normal': both('fs/smb/client/reparse.c', 718, 726, 'le16_to_cpu(buf->ReparseDataLength) != 0') +
                       both('fs/smb/common/smb2pdu.h', 1513, 1517, 'ReparseDataLength'),
}
raws = {label: load(STAGE / 'consumer' / 'raw' / (label + '.json')) for label in REVISIONS}
assert all(row['revision'] == REVISIONS[label] for label, row in raws.items())
assert all(row['source_file'] == 'fs/smb/client/reparse.c' for row in raws.values())
assert all(row['counts'] == {'candidate': 0, 'normal': 1, 'insufficient': 2} for row in raws.values())
assert raws['parent']['findings'] == raws['fixed']['findings']
assert all(row['source_line'] != 679 for raw in raws.values() for row in raw['findings'])

review = {
    'schema_version': 1, 'date': '2026-10-03', 'role': 'consumer',
    'scope': 'Post-unseal manual review of the preselected SMB input; no rule/CLI rerun, sample/file replacement, compile or model execution',
    'case_identity': {'commit': REVISIONS['fixed'], 'parent': REVISIONS['parent'],
                      'selected_source': 'fs/smb/client/reparse.c',
                      'selection_exposure': 'title-informed metadata selection; no match in defined local prior-record roots, not proof of unseen by any human',
                      'new_confirmed_case_count': 0},
    'target': {'function': 'parse_reparse_wsl_symlink', 'line': 679,
               'expression_role': 'fourth argument output-buffer pointer to utf8s_to_utf16s',
               'parent_expression': 'symname_utf16', 'fixed_expression': '(wchar_t *) symname_utf16',
               'local_variable_type': '__le16 *', 'api_parameter_type': 'wchar_t *',
               'api_wchar_t': 'typedef u16 wchar_t',
               'patch_change': 'explicit pointer cast; endian selector, input, lengths, allocation and consumers unchanged in the patch',
               'commit_stated_purpose': 'remove compiler warning; diagnostic tool/options not reproduced',
               'format_change_supported': False,
               'behavioral_endian_defect_supported': False,
               'quotes': ['target_parent', 'target_fixed', 'nls_declaration']},
    'machine_result': {'parent_raw': 'consumer/raw/parent.json', 'parent_raw_sha256': sha(STAGE / 'consumer/raw/parent.json'),
                       'fixed_raw': 'consumer/raw/fixed.json', 'fixed_raw_sha256': sha(STAGE / 'consumer/raw/fixed.json'),
                       'counts_each': {'candidate': 0, 'normal': 1, 'insufficient': 2},
                       'candidate_count': 0,
                       'target_emitted': False, 'target_status': 'outside_direct_if_struct_field_read_grammar',
                       'target_is_machine_normal': False,
                       'reported_normal_relation_to_target': 'different function and different expression; cannot serve as a target diagnosis',
                       'automatic_fact_scope': ['syntactic field declaration', 'if-condition textual reference', 'restricted classification', 'files/SHA'],
                       'not_automatic_facts': ['wchar_t prototype contract', 'UTF16 endian-selector semantic meaning',
                                               'API output implementation', 'buffer input/consumer chain',
                                               'sizeof operand is unevaluated', 'compile diagnostic or runtime correctness']},
    'reported_sites_manual_review': [
        {'function': 'parse_reparse_posix', 'line': 485, 'field': 'InodeType',
         'original_status': 'insufficient', 'expression': 'len < sizeof(buf->InodeType)',
         'actual_value_read': False,
         'interpretation': 'Fixed-size scalar sizeof operand is unevaluated; a type/size reference, not an endian-sensitive scalar consumption. The nearby actual InodeType value is explicitly converted in a switch, outside the original if-only grammar.',
         'quotes': ['reported_sizeof_posix']},
        {'function': 'parse_reparse_wsl_symlink', 'line': 659, 'field': 'Flags',
         'original_status': 'insufficient', 'expression': 'len <= sizeof(buf->Flags)',
         'actual_value_read': False,
         'interpretation': 'Fixed-size __le32 member in sizeof is unevaluated. This emitted position belongs to the target function but does not read Flags or diagnose the output-buffer argument at line 679.',
         'quotes': ['reported_sizeof_wsl']},
        {'function': 'parse_reparse_point', 'line': 722, 'field': 'ReparseDataLength',
         'original_status': 'normal', 'expression': 'le16_to_cpu(buf->ReparseDataLength) != 0',
         'actual_value_read': True,
         'interpretation': 'One actual field access explicitly converts the length, so a local expression normal is source-supported; these non-symlink dispatch cases and this length check do not prove target or whole-function correctness.',
         'manual_access_occurrence_count': 1, 'quotes': ['reported_normal']},
    ],
    'reviewed_format_and_consumption': {
        'type_diagnostic_layer': 'Source signature supports why the explicit cast aligns the argument type; commit reports a warning. Specific compiler/checker diagnostic is unknown without a build.',
        'api_format_authority': 'Same-revision nls implementation is the local API semantic authority: explicit UTF16_LITTLE_ENDIAN selects __cpu_to_le16 writes via put_utf16; the buffer pointer spelling does not choose byte order.',
        'api_format_supported_for_both_versions': True,
        'input_value_source': 'WSL PathBuffer is declared __u8 UTF-8 with no nul terminator. Local smb2_parse_reparse_point derives buf from the supplied SMB IOCTL rsp_iov OutputOffset/OutputCount; parse_reparse_point dispatches LX_SYMLINK to the target.',
        'input_validation_and_flow': 'Target converts ReparseDataLength, subtracts fixed Flags size, rejects embedded nul, allocates local output, passes explicit LE selector, handles conversion errors, doubles returned u16 count to bytes, then feeds unicode=true to cifs_strndup_from_utf16.',
        'direct_consumer': 'cifs_strndup_from_utf16 treats unicode input as __le16, computes output size and calls cifs_from_utf16; that local conversion reads with get_unaligned_le16.',
        'representation_relation': 'Explicit little-endian producer selection and little-endian consumer interpretation are source-supported before and after the cast. The patch does not establish a data-format change or a prior endian-failure chain.',
        'local_entry_binding': 'smb2ops contains .parse_reparse_point = smb2_parse_reparse_point bindings; full upstream invocation, network bytes and deployment were not traced.',
        'external_protocol_authority_reviewed': False,
        'real_runtime_or_build_observed': False,
        'quotes': ['nls_format_implementation', 'wsl_input_declaration', 'local_input_and_dispatch', 'ops_binding', 'utf16_consumer']},
    'five_dimension_initial_codes': {
        'dates': {'fix_committer_date_from_unsealed_patch': '2024-12-09',
                  'discovery_date': 'unknown', 'fault_introduction_date': 'unknown',
                  'fixes_metadata': '06a7adf318a3 (cifs: Add support for parsing WSL-style symlinks), not independently reviewed',
                  'introduction_to_discovery_or_discovery_to_fix_intervals': 'unknown; no date chasing in this bounded review'},
        'architecture_platform': {'code': 'no_specific_CPU_architecture_trigger_supported',
                                  'context': 'SMB WSL-style symlink parser; WSL-style refers to reparse format, not proof of executing Linux under WSL',
                                  'build_diagnostic_environment': 'unknown'},
        'subsystem_interface': {'code': 'fs/smb/client -> NLS UTF-8/UTF-16 API',
                                'boundary': 'typed output pointer plus explicit format selector and local UTF16 consumer'},
        'vertical_horizontal_relation': {'code': 'no_confirmed_cross_architecture_vertical_or_horizontal_fault',
                                         'source_layers': 'filesystem calls shared NLS; software call layering alone does not confirm architecture mismatch'},
        'introduction_side': {'code': 'SMB callsite type annotation; behavioral fault introduction unknown',
                              'reported_history': 'Fixes metadata attributes parsing support; no prior source/history expansion',
                              'confirmed_defect_case': False}},
    'classification': {'protocol_bucket': 'target_outside_rule_coverage_and_not_this_behavioral_endian_mechanism',
                        'scope_result': 'zero_candidate_positions_for_fixed_input; cannot claim target machine normal, true negative, accuracy, or whole-file safety',
                        'human_result': 'compiler/type-warning cast repair with unchanged explicit UTF16 representation selector and supported local producer/consumer relation',
                        'added_confirmed_cases': 0},
    'support_flags': {'patch_target_located_in_selected_file': True,
                      'original_rule_emits_target': False,
                      'nls_prototype_and_endian_implementation_reviewed': True,
                      'local_utf8_input_and_utf16_consumer_relation_supported': True,
                      'type_warning_purpose_supported_by_commit': True,
                      'specific_warning_reproduced': False,
                      'data_format_change_supported': False,
                      'behavioral_endian_bug_chain_supported': False,
                      'actual_architecture_config_or_network_io_established': False,
                      'external_SMB_specification_reviewed': False},
    'unknown_flags': ['compiler_checker_and_warning_options', 'generated_config_build_and_real_architecture',
                      'actual_server_payload_values', 'full_network_entry_to_dispatch_reachability',
                      'external_SMB_format_specification', 'discovery_date_and_fault_introduction_date',
                      'whole_function_correctness'],
    'quotes': quotes,
    'integrity': {'parents_lock_sha256': sha(STAGE / 'parents_lock.json'),
                  'pre_freeze_sha256': sha(STAGE / 'freeze_pre.json'),
                  'unseal_manifest_sha256': sha(STAGE / 'unseal_manifest.json'),
                  'patch_unsealed_sha256': sha(STAGE / 'consumer/patch_unsealed.txt'),
                  'protocol_sha256': sha(STAGE / 'protocol_pre.md'),
                  'source_manifest_sha256': sha(STAGE / 'source_manifest.json'),
                  'source_manifest_extra_sha256': sha(HERE / 'source_manifest_extra.json'),
                  'new_support_sources_per_revision': 4, 'new_support_source_total': 8,
                  'source_quote_schema': 'revision/source_path/saved_path(stage-relative)/start_line/end_line/text/sha256/blob_sha1',
                  'capture_commands': 'consumer/manual_review/commands_extra.json',
                  'review_builder_sha256': sha(Path(__file__).resolve()),
                  'old_sources_raw_protocol_rules_untouched': True,
                  'no_analyzer_rerun_compile_model_or_sample_expansion': True},
}
(HERE / 'review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
summary = {'review_json_sha256': sha(HERE / 'review.json'), 'target_line': 679,
           'target_emitted': False, 'format_change_supported': False, 'new_confirmed_cases': 0,
           'source_quote_count': sum(map(len, quotes.values())), 'new_source_count': 8}
(HERE / 'raw' / 'build_review.stdout').write_text(json.dumps(summary) + '\n', encoding='utf-8')
print(json.dumps(summary))
