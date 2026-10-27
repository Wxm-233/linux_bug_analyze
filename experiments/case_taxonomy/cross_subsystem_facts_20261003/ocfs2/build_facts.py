"""Assemble explicitly reviewed facts from saved evidence; no kernel/model run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = read('source_manifest.json')
prepared = read('prepared.json')
replay = read('replay.json')
tool_before = read('tool_before_replay.json')
tool_after = read('tool_after_replay.json')
assert tool_before == tool_after == read('final_tool_state.json')


def ref(label, path, start, end=None, expected=None):
    revision = {'parent': 'c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4^',
                'fix': 'c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4'}[label]
    entry = next(item for item in manifest if item['revision'] == revision and item['path'] == path)
    saved = HERE / entry['saved_path']
    assert digest(saved) == entry['sha256']
    lines = saved.read_text(encoding='utf-8').splitlines()
    excerpt = '\n'.join(lines[start-1:(end or start)])
    if expected is not None:
        assert expected in excerpt, (path, start, expected)
    return {'revision': prepared['resolved_revisions'][label], 'path': path,
            'line_start': start, 'line_end': end or start,
            'blob': entry['blob'], 'sha256': entry['sha256'],
            'saved_path': entry['saved_path'], 'excerpt': excerpt}


def both_inode(start, end=None, expected=None):
    # The reviewed fix adds two source lines after the target function.
    return [ref('parent', 'fs/ocfs2/inode.c', start, end, expected),
            ref('fix', 'fs/ocfs2/inode.c', start+2 if start > 212 else start,
                (end+2 if end > 212 else end) if end else None, expected)]


manual = [
    {'id': 'R1', 'kind': 'local_disk_format', 'support': 'supported_by_local_source',
     'fact': 'ocfs2_dinode is explicitly documented as an on-disk inode; i_flags is a direct __le32 member. This establishes the local source representation contract, not measured runtime bytes or an independently reviewed external specification.',
     'evidence': [ref(label, 'fs/ocfs2/ocfs2_fs.h', 660, 678, '__le32 i_flags') for label in ('parent', 'fix')]},
    {'id': 'R2', 'kind': 'host_mask_values', 'support': 'supported_by_local_source',
     'fact': 'The primary mask macros are ordinary integer constants: SUPER_BLOCK=0x20, LOCAL_ALLOC=0x40, CHAIN=0x400, DEALLOC=0x800; their OR is 0x00000c60. The analyzer only labels a bitmask pattern; it does not expand these macros or compute this value.',
     'manual_macro_values': {'OCFS2_SUPER_BLOCK_FL': '0x00000020', 'OCFS2_LOCAL_ALLOC_FL': '0x00000040',
                             'OCFS2_CHAIN_FL': '0x00000400', 'OCFS2_DEALLOC_FL': '0x00000800'},
     'manual_or_value': '0x00000c60',
     'evidence': [ref(label, 'fs/ocfs2/ocfs2_fs.h', 213, 221) for label in ('parent', 'fix')]},
    {'id': 'R3', 'kind': 'representation_conversion_contract', 'support': 'supported_by_local_source',
     'fact': 'generic.h maps le32_to_cpu to __le32_to_cpu. The selected big-endian implementation byte-swaps a little-endian word, whereas the little-endian implementation only casts. This supports a conditional source mismatch when the big-endian implementation applies; no preprocessing/build execution was performed.',
     'evidence': [ref(label, path, start, end) for label in ('parent', 'fix') for path, start, end in
                  [('include/linux/byteorder/generic.h', 88, 89),
                   ('include/uapi/linux/byteorder/big_endian.h', 34, 35),
                   ('include/uapi/linux/byteorder/little_endian.h', 34, 35),
                   ('include/uapi/linux/types.h', 27, 40)]]},
    {'id': 'R4', 'kind': 'primary_consumption', 'support': 'source_supported_conditional_contract_mismatch',
     'fact': 'The parent primary directly masks the raw on-disk word with host constants; the fix converts that read with le32_to_cpu before applying exactly the same mask. Each reviewed condition contains one i_flags access, so this primary does not exercise the analyzer\'s repeated-text binding limitation.',
     'parent_runtime_verdict': 'unknown', 'fix_whole_function_verdict': 'not_claimed',
     'evidence': [ref('parent', 'fs/ocfs2/inode.c', 201, 206, 'if (di->i_flags &'),
                  ref('fix', 'fs/ocfs2/inode.c', 201, 207, 'le32_to_cpu(di->i_flags)')]},
    {'id': 'R5', 'kind': 'direct_consumer_and_effect', 'support': 'supported_by_local_source',
     'fact': 'The only direct call found in same-revision fs/ocfs2 is in ocfs2_filecheck_repair_inode_block. A true return permits interpreting id2 as an extent list and potentially changing l_next_free_rec; changed metadata causes checksum recomputation and a dirty buffer. This is a source-level potential consequence, not observed corruption.',
     'consumer_search': ['raw/parent_consumer_search.stdout', 'raw/fix_consumer_search.stdout'],
     'evidence': both_inode(1637, 1652, 'ocfs2_dinode_has_extents(di)') +
                 [ref(label, 'fs/ocfs2/ocfs2_fs.h', 726, 735) for label in ('parent', 'fix')]},
    {'id': 'R6', 'kind': 'consumer_gates', 'support': 'supported_by_local_source',
     'fact': 'Repair returns immediately when its validation succeeds. Reaching the primary requires that validation fail, filesystem not be hard/soft read-only, buffer not be journal-owned, signature be valid, and VALID_FL remain set. i_blkno/fs_generation may be repaired before the primary. The special flags are not converted or rewritten before this read.',
     'evidence': both_inode(1577, 1639)},
    {'id': 'R7', 'kind': 'disk_value_source', 'support': 'supported_by_local_source_with_runtime_conditions',
     'fact': 'The repair callback casts bh->b_data to struct ocfs2_dinode. The filecheck read helper supplies that callback to ocfs2_read_blocks when type is nonzero. ocfs2_read_blocks allocates/obtains a buffer at the inode block number, submits READ when appropriate, waits for success, then calls validate(sb,bh) only when the buffer needs validation. It may use cached data or skip journal/dirty buffers, so disk I/O is a conditional source path.',
     'evidence': both_inode(1577, 1584, 'bh->b_data') + both_inode(1658, 1675, 'ocfs2_filecheck_repair_inode_block') +
                 [ref(label, 'fs/ocfs2/buffer_head_io.c', start, end) for label in ('parent', 'fix')
                  for start, end in [(193, 202), (231, 245), (283, 292), (326, 331), (361, 384)]]},
    {'id': 'R8', 'kind': 'local_trigger_chain', 'support': 'supported_by_local_source_with_runtime_conditions',
     'fact': 'The filecheck fix sysfs operation passes FILECHECK_FIX to ocfs2_iget; only an I_NEW inode invokes ocfs2_read_locked_inode. Its can_lock branch uses the filecheck helper with type=1 and IGNORE_CACHE, and its alternate sync-read branch invokes repair when FILECHECK_FIX is set and the buffer is not journal-owned. A cached inode can bypass this chain.',
     'evidence': [ref(label, 'fs/ocfs2/filecheck.c', 405, 443) for label in ('parent', 'fix')] +
                 both_inode(140, 158, 'ocfs2_read_locked_inode') + both_inode(520, 522, 'can_lock') +
                 both_inode(568, 594, 'ocfs2_filecheck_repair_inode_block') +
                 [ref(label, 'fs/ocfs2/inode.h', 120, 125, 'OCFS2_FI_FLAG_FILECHECK_FIX') for label in ('parent', 'fix')]},
    {'id': 'R9', 'kind': 'normal_control', 'support': 'supported_for_this_read_only',
     'fact': 'Preselected control is same-function i_size as a nonzero/presence read; same-condition i_clusters==0 is auxiliary. Zero and nonzero remain unchanged by byte swapping, so these reads are locally normal even in the parent. The parent i_mode subexpression is a separate excluded candidate, preventing a whole-if correctness claim. The fix adds explicit conversions, but these two zero/presence reads did not themselves require conversion.',
     'evidence': [ref('parent', 'fs/ocfs2/inode.c', 208, 208, 'di->i_size && di->i_clusters == 0'),
                  ref('fix', 'fs/ocfs2/inode.c', 209, 210, 'le64_to_cpu(di->i_size)')]},
    {'id': 'R10', 'kind': 'existing_same_representation_context', 'support': 'supported_for_this_read_only',
     'fact': 'An existing i_flags read in ocfs2_populate_inode converts its mask with cpu_to_le32(OCFS2_SYSTEM_FL), putting both bitwise operands in the same representation. This context was in the original tool input and remains a local normal; it is not another primary or new case.',
     'evidence': both_inode(398, 399, 'cpu_to_le32(OCFS2_SYSTEM_FL)')},
    {'id': 'R11', 'kind': 'source_configuration_scope', 'support': 'supported_source_range_only',
     'fact': 'OCFS2_FS is tristate with INET && SYSFS && CONFIGFS_FS dependencies; its Makefile includes inode.o, buffer_head_io.o and filecheck.o in ocfs2. The primary/caller has no enclosing CONFIG_OCFS2_DEBUG_FS guard. Source files permit describing a compiled scope, but dependency satisfiability, generated config, mount and actual I/O are not established.',
     'evidence': [ref(label, path, start, end) for label in ('parent', 'fix') for path, start, end in
                  [('fs/Kconfig', 50, 50), ('fs/ocfs2/Kconfig', 2, 12),
                   ('fs/ocfs2/Makefile', 4, 6), ('fs/ocfs2/Makefile', 11, 44)]] +
                 both_inode(1577, 1682)},
    {'id': 'R12', 'kind': 'big_endian_source_implementation', 'support': 'supported_source_choice_not_build',
     'fact': 'Saved PowerPC source offers an endian choice and its asm byteorder header selects big- or little-endian headers. This shows a source implementation context for the conditional contract only; no specific configuration was solved or built, and no real big-endian execution was observed.',
     'evidence': [ref(label, path, start, end) for label in ('parent', 'fix') for path, start, end in
                  [('arch/powerpc/platforms/Kconfig.cputype', 604, 625),
                   ('arch/powerpc/include/uapi/asm/byteorder.h', 11, 15),
                   ('include/linux/byteorder/big_endian.h', 5, 11)]]},
    {'id': 'R13', 'kind': 'format_and_effect_limits', 'support': 'unknown_external_and_runtime',
     'fact': 'No independent external OCFS2 disk-format specification, filesystem image bytes, deployed big-endian build/config, mounted inode flags, callback trace, or resulting corruption was collected. Local source supports the representation/consumer relationship; it cannot establish those missing facts.'},
]

automatic = {}
for label in ('parent', 'fix'):
    raw = read(f'raw/{label}.json')
    result = replay['results'][label]
    primary = result['primary']
    assert primary['condition'].count('di->i_flags') == 1
    controls = result['normal_control_reads']
    assert all(row['condition'].count('di->' + row['field']) == 1 for row in controls)
    automatic[label] = {'raw_output': result['raw_output'], 'raw_sha256': result['raw_output_sha256'],
                        'revision': raw['revision'], 'resolved_revision': prepared['resolved_revisions'][label],
                        'source_file': raw['source_file'], 'source_sha256': raw['source_sha256'],
                        'files_read': raw['files_read'], 'include_notes': raw['include_notes'],
                        'primary': primary, 'normal_control_reads': controls,
                        'background_whole_file_counts': raw['counts'],
                        'scope': raw['scope']}

facts = {
    'schema_version': 1, 'date': '2026-10-03', 'stage': 'cross_subsystem_facts_20261003',
    'identity': {'case': 'previously_read_ocfs2_development_interface',
                 'primary': 'ocfs2_dinode_has_extents:ocfs2_dinode.i_flags',
                 'comparison': 'known_parent_fix_replay', 'blind_validation': False,
                 'new_case_count': 0, 'interface_inventory_count': 1,
                 'other_candidates': 'i_mode and i_dyn_features excluded from primary; only replay background'},
    'selection': {**{key: value for key, value in prepared.items() if key != 'phase'},
                  'phase_at_selection': prepared['phase'],
                  'snapshot_note': 'Historical pre-replay selection snapshot; formal replay is complete as recorded in replay.json'},
    'automatic_facts': {'provenance': 'unmodified endian_consumer_single_revision.py original CLI stdout',
                        'obtained': ['field declaration/type/line', 'parameter struct pointer binding',
                                     'if condition text', 'direct-use syntactic pattern/status/reason',
                                     'same-revision files read and SHA', 'whole-file background counts'],
                        'not_obtained': ['macro numeric expansion', 'actual disk value or value domain',
                                         'interprocedural caller/data flow', 'ABI/format authority',
                                         'preprocessor/config evaluation', 'architecture or I/O execution',
                                         'runtime bug or whole-function safety'],
                        'revisions': automatic},
    'reviewed_facts': {'provenance': 'manual inspection of saved same-revision local Git source',
                       'entries': manual},
    'support_flags': {'primary_occurrence_binding_reviewed': True,
                      'control_occurrence_binding_reviewed': True,
                      'local_disk_format_contract_supported': True,
                      'host_mask_numeric_values_reviewed': True,
                      'direct_consumer_found': True,
                      'conditional_disk_to_buffer_to_read_chain_found': True,
                      'source_configuration_range_found': True,
                      'source_conditional_big_endian_mismatch_supported': True,
                      'external_disk_format_specification_reviewed': False,
                      'actual_big_endian_build_config_established': False,
                      'actual_big_endian_kernel_execution_established': False,
                      'actual_disk_flags_or_corruption_observed': False,
                      'whole_function_correctness_established': False,
                      'no_new_input_or_candidate_promotion': True},
    'unknown_flags': ['external_disk_format_authority', 'full_preprocessing_and_config_satisfiability',
                      'specific_big_endian_build_and_mount', 'actual_special_flag_value_at_runtime',
                      'validation_failure_and_callback_reachability_in_real_io', 'observed_runtime_corruption'],
    'verdict': {'parent_primary': 'conditional_source_representation_mismatch_supported',
                'fix_primary': 'explicit_conversion_matches_reviewed_local_contract',
                'normal_controls': 'local_zero_presence_reads_supported',
                'runtime': 'unknown; no kernel execution or build',
                'measurement_unit': 'one already-read interface facts inventory, zero new cases'},
    'integrity': {'original_script_sha256_before': tool_before['script_sha256'],
                  'original_script_sha256_after': tool_after['script_sha256'],
                  'protocol_sha256_before': tool_before['protocol_sha256'],
                  'protocol_sha256_after': tool_after['protocol_sha256'],
                  'script_direct_stdlib_imports_unchanged': tool_before['imports'] == tool_after['imports'],
                  'scope_of_dependency_hashes': 'Direct imported module origins; not recursive standard-library/binary dependency closure',
                  'tool_state_files': ['tool_before.json', 'tool_after_prepare.json', 'tool_before_replay.json',
                                       'tool_after_replay.json', 'final_tool_state.json'],
                  'runner_sha256_at_facts_lock': digest(HERE / 'runner.py'),
                  'facts_builder_sha256': digest(Path(__file__).resolve()),
                  'all_saved_source_count': len(manifest),
                  'source_manifest': 'source_manifest.json', 'command_log': 'commands.json',
                  'transport_note': 'WSL localhost/NAT warning in transport is not part of any SHA or Git stdout. Hashes are validated from saved process bytes.'},
}
(HERE / 'facts.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
summary = {'facts_file': 'facts.json', 'facts_sha256': digest(HERE / 'facts.json'),
           'primary_status': {label: automatic[label]['primary']['status'] for label in automatic},
           'new_cases': 0, 'saved_sources': len(manifest)}
(HERE / 'raw' / 'build_facts_final.stdout').write_text(json.dumps(summary) + '\n', encoding='utf-8')
print(json.dumps(summary))
