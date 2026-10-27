"""Finite die source adapter: definition timeline plus reviewed versioned policy.

This is a fact extractor for the known case, not semantic policy inference.
The unchanged generic evaluator handles the explicit relation and evidence tier.
"""
from pathlib import Path
import ast
import copy
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
LEGACY = HERE.parent / 'die_contract_transfer_20261019'
sys.path.insert(0, str(LEGACY))
import transfer as legacy
from projection import project_static, ID_MACRO, MASK_MACRO, FLAG, ATTRS
sys.path.insert(0, str(HERE.parent / 'runtime_source_binding_20261020'))
from binding import PROFILES, SHORT_BODIES, REVIEWED_BLOBS, PUBLIC, X86, S390, DRIVER

NAMES = (ID_MACRO, MASK_MACRO, FLAG)
CORE = INNER / 'linux_bug_analyze/contract_protocol.py'
CORE_SHA = '42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def need(value, reason):
    if not value:
        raise ValueError(reason)

def normalize(value):
    return re.sub(r'\s+', '', value)

def parse(text, root):
    """Track the target macros at expansion sites and compiled table selection."""
    marker = re.compile(r'^#\s+(\d+)\s+("(?:[^"\\]|\\.)*")(?:\s+\d+)*\s*$')
    directive = re.compile(r'^#(define|undef)\s+(' + '|'.join(NAMES) + r')(?=\(|\s|$)')
    events, state, snapshots, locations = [], {}, {}, []
    filename, source_line = '<unknown>', 0
    lines = text.splitlines()
    for index, line in enumerate(lines, 1):
        mark = marker.match(line)
        if mark:
            filename, source_line = ast.literal_eval(mark[2]), int(mark[1])
            continue
        locations.append((index, filename, source_line))
        match = directive.match(line)
        if match:
            event = {'action': match[1], 'name': match[2], 'definition': line,
                     'file': filename, 'source_line': source_line, 'preprocessed_line': index}
            events.append(event)
            if match[1] == 'define':
                state[match[2]] = event
            else:
                state.pop(match[2], None)
        # Macro expansion has already happened in this line. Its state is the
        # source state at this use, not the final macro dictionary after the TU.
        for name, pattern in [('id_expansion', r'^static ssize_t die_id_show\('),
                              ('mask_expansion', r'^static ssize_t die_cpus_read\('),
                              ('bin_table', r'^static struct bin_attribute \*bin_attrs\[\]'),
                              ('id_table', r'^static struct attribute \*default_attrs\[\]')]:
            if re.search(pattern, line):
                need(name not in snapshots, 'ambiguous_use:' + name)
                snapshots[name] = {'preprocessed_line': index, 'file': filename, 'source_line': source_line,
                                   'macro_state': copy.deepcopy(state), 'expanded_line': line}
        source_line += 1
    need(set(snapshots) >= {'bin_table', 'id_table'}, 'complete_attribute_tables_missing')
    pp = {'macro_definitions': {}, 'arrays': {}, 'declarations': {}}
    for name in NAMES:
        row = snapshots['bin_table']['macro_state'].get(name)
        pp['macro_definitions'][name] = [{key: value for key, value in row.items() if key not in {'name', 'action'}}] if row else []
    for name, kind in [('default_attrs', 'attribute'), ('bin_attrs', 'bin_attribute')]:
        matches = list(re.finditer(r'static struct ' + kind + r'\s*\*' + name + r'\[\]\s*=\s*\{.*?\};', text, re.S))
        need(len(matches) == 1, 'array_missing_or_ambiguous:' + name)
        raw = matches[0][0]
        refs = [attr for attr in ATTRS if re.search(r'&' + attr + r'\b', raw)]
        pp['arrays'][name] = {'text': raw, 'die_references': refs}
    for attr in ATTRS:
        pp['declarations'][attr] = len(re.findall(r'^static struct (?:device_attribute|bin_attribute)\s+' + attr + r'\s*=', text, re.M)) == 1
    return {'events': events, 'snapshots': snapshots, 'pp': pp, 'source_tree': root,
            'effective_definition_state_at_whole_TU_end': copy.deepcopy(state),
            'parser_scope': 'GCC -dD markers, reviewed die definitions, three compiled attributes and two arrays'}

def project(parsed, source_arch):
    result = project_static(parsed['pp'], parsed['source_tree'], source_arch)
    unknowns = result['unknowns']
    expected = {ID_MACRO: {'native': SHORT_BODIES['native_id'], 'fallback': SHORT_BODIES['fallback_id']},
                MASK_MACRO: {'native': SHORT_BODIES['native_mask'], 'fallback': SHORT_BODIES['fallback_mask']}}
    snapshots = parsed['snapshots']
    for name, role in [(ID_MACRO, 'id'), (MASK_MACRO, 'mask')]:
        rows = parsed['pp']['macro_definitions'].get(name, [])
        if len(rows) != 1:
            unknowns.append('effective_definition_missing:' + name)
            continue
        row = rows[0]
        key = 'native' if result.get(role + '_native') is True else 'fallback'
        if normalize(row['definition']) != normalize(expected[name][key]):
            unknowns.append('unreviewed_effective_body:' + name)
        for point in ['bin_table', 'id_table'] + ([role + '_expansion'] if result.get('listed_any') else []):
            current = snapshots.get(point, {}).get('macro_state', {}).get(name)
            if current is None or any(current.get(k) != row.get(k) for k in ['definition', 'file', 'source_line', 'preprocessed_line']):
                unknowns.append('definition_changed_between_expansion_and_table:' + name + ':' + point)
    for name in ['bin_table', 'id_table']:
        if snapshots[name]['file'] != parsed['source_tree'] + '/' + DRIVER:
            unknowns.append('table_outside_reviewed_driver:' + name)
    if result.get('listed_any'):
        for point in ['id_expansion', 'mask_expansion']:
            if snapshots.get(point, {}).get('file') != parsed['source_tree'] + '/' + DRIVER:
                unknowns.append('expansion_outside_reviewed_driver:' + point)
    result['provider_body_reviewed'] = not unknowns
    result['status'] = 'supported' if not unknowns else 'insufficient'
    result['evidence_tier'] = 'new_full_TU_reconstruction_of_archived_build_context'
    result['historical_runtime_origin_proved'] = False
    return result

def verify(profile):
    root = HERE / 'preprocessing' / profile
    receipt = json.loads((root / 'receipt.json').read_bytes())
    revision, arch = PROFILES[profile]
    build = json.loads((legacy.BASE / 'runtime/profiles' / profile / 'build.json').read_bytes())
    need(receipt['profile'] == build['profile'] == profile and receipt['revision'] == build['revision'] == revision, 'profile_revision_mismatch')
    need(receipt['arch'] == arch == build['arch'] and receipt['returncode'] == 0, 'architecture_or_completion_mismatch')
    need(receipt['before_sha256'] == receipt['after_sha256'], 'original_build_changed')
    need(receipt['before_sha256']['config'] == build['config_sha256'], 'configuration_identity_mismatch')
    need(receipt['before_sha256']['image'] == build['image_sha256'], 'image_identity_mismatch')
    need(sha(root / 'topology.i') == receipt['preprocessed_sha256'], 'preprocessed_identity_mismatch')
    need(sha(root / 'include_provenance.json') == receipt['include_provenance_sha256'], 'include_identity_mismatch')
    need(sha(legacy.BASE / 'runtime/profiles' / profile / 'build.json') == receipt['build_json_sha256'], 'archive_build_changed')
    provenance = json.loads((root / 'include_provenance.json').read_bytes())
    need(all(row['kind'] in ['pinned_source', 'generated_build_input'] for row in provenance), 'unreviewed_external_include')
    need(all(row['git_blob'] == row['actual_blob'] and row['matches_pinned_revision'] is True for row in provenance if row['kind']=='pinned_source'), 'source_revision_mismatch')
    by_name = {row.get('source_path'): row for row in provenance if row['kind']=='pinned_source'}
    required = [PUBLIC, DRIVER, X86 if arch == 'x86_64' else S390]
    need(all(by_name.get(name, {}).get('git_blob') == REVIEWED_BLOBS[revision][name] for name in required), 'outside_reviewed_direct_files')
    need(receipt['source_tree'] == build['source_tree'] and receipt['build_directory'] == build['build_directory'], 'source_context_mismatch')
    return receipt

def envelope(profile, projection, evidence):
    revision, _ = PROFILES[profile]
    context = 'source.runtimeconfig.' + profile + '.' + sha(evidence)[:16]
    result = legacy.envelope(profile, revision, 'source_projection', context, projection, True, evidence)
    # Keep the old generic contract and policy, but describe this new evidence
    # tier correctly. There is deliberately no archived_runtime promotion.
    result['ledger']['claims']['review.provider_binding']['statement'] = 'Effective definitions in a new complete TU reconstruction with this archived configuration, reviewed finite bodies; not historical preprocessing or physical topology truth.'
    for row in result['ledger']['claims'].values():
        if row.get('role') == 'fact':
            row['statement'] = 'Program fact from new full-TU reconstruction; historical runtime source remains unproved.'
    return result

def evaluate(item):
    try:
        need(sha(CORE) == CORE_SHA, 'common_core_changed')
        revision = item['contract']['revision']
        expected = 'counterfactual_policy_from_fixed' if revision == legacy.OLD else 'repair_policy_application'
        need(revision in [legacy.OLD, legacy.FIXED], 'unreviewed_context_revision')
        policy = item['ledger']['documents']['policy_application']
        need(policy['source_policy_revision'] == item['ledger']['source_policy_revision'] == legacy.FIXED, 'source_policy_revision_mismatch')
        need(item['policy_application'] == policy['interpretation'] == expected, 'policy_application_not_versioned')
        need(item['historical_normative_verdict'] == 'insufficient', 'unsupported_historical_normative_verdict')
        return legacy.evaluate_contract(item['contract'], item['ledger'], item['record'])
    except (ValueError, KeyError, TypeError) as exc:
        return {'relation_at_observation': 'insufficient', 'relation_at_deadline': 'insufficient', 'whole_path': 'insufficient', 'reasons': [str(exc)]}
