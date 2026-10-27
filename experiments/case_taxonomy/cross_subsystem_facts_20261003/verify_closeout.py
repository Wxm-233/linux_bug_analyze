"""Verify saved known-case facts, quotations, raw reports and prior locks.

No replay, Git query, compiler, device or model is invoked.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES = HERE.parent
PRIOR = RULES / 'request_copy_boundary_20261002'
PRIOR_LOCKS = {
    'freeze_manifest.json': '2e51a42f38f4a51720e021a1cda0b7151f6b2daa55734076edb06bf6489cfce9',
    'completion_manifest.json': 'f6cbdff4ade18b87e4f6c5a2082ea5e6920039d5e848b9fe02418ff621bf923b',
}
TOOLS = {
    'endian_consumer_single_revision.py': '71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c',
    'endian_producer_single_revision.py': '5f0a2823c0a3cc7eec501ab0f4478fb4c578e4a561becc61326e6a46880fe786',
}
PROTOCOL = '1177e42163992884eed62023cab877e636f2e137d4664c0f0fbbfc795d21b44f'


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(base, relative):
    # Raw PWM manifests use Windows separators. Normalize for portability.
    path = (base / relative.replace('\\', '/')).resolve()
    require(path.is_relative_to(base.resolve()), 'path escapes ' + str(base))
    return path


def check(records):
    for item in records:
        require(sha(safe(RULES, item['path'])) == item['sha256'], 'locked file ' + item['path'])
    return records


def save_once(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def sources(case, manifests):
    found = {}
    for name in manifests:
        for item in read(case / name):
            if item.get('available') is False:
                require('saved_path' not in item, 'missing source cannot claim a saved file')
                continue
            path = safe(case, item['saved_path'])
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            require(digest == item['sha256'], 'source SHA ' + str(path))
            require(blob == item.get('blob', item.get('blob_oid')), 'source blob ' + str(path))
            lines = raw.decode('utf-8').splitlines()
            require(len(lines) == item['line_count'], 'source line count ' + str(path))
            require(item.get('bytes', len(raw)) == len(raw), 'source byte count ' + str(path))
            if path in found:
                require(found[path]['sha256'] == digest, 'conflicting source manifest')
            found[path] = dict(item, decoded_lines=lines)
    return found


def quotations(case, facts, source_map):
    count = 0
    for item in walk(facts):
        if {'saved_source', 'source_excerpt', 'line_start', 'line_end'}.issubset(item):
            saved, excerpt, digest, blob = (item['saved_source'], item['source_excerpt'],
                                           item['source_sha256'], item['blob_oid'])
        elif {'saved_path', 'excerpt', 'line_start', 'line_end'}.issubset(item):
            saved, excerpt, digest, blob = item['saved_path'], item['excerpt'], item['sha256'], item['blob']
        else:
            continue
        path = safe(case, saved)
        require(path in source_map, 'quotation not bound to saved source')
        source = source_map[path]
        require(digest == source['sha256'] and blob == source.get('blob', source.get('blob_oid')),
                'quotation identity')
        require(1 <= item['line_start'] <= item['line_end'] <= len(source['decoded_lines']), 'quotation range')
        original = '\n'.join(source['decoded_lines'][item['line_start'] - 1:item['line_end']])
        require(excerpt == original, 'literal quotation ' + str(path))
        count += 1
    require(count > 0, 'no machine-checkable quotations ' + case.name)
    return count


def commands(case, logs):
    count = 0
    success = 0
    for name in logs:
        for item in read(case / name):
            require(isinstance(item['returncode'], int), 'command outcome missing')
            # Historical unavailable paths may have nonzero Git-show results.
            for stream in ('stdout', 'stderr'):
                require(sha(safe(case, item[stream])) == item[stream + '_sha256'], 'raw command stream')
            count += 1
            success += item['returncode'] == 0
    return dict(recorded=count, successful=success, nonzero_retained=count - success)


def raw_report(case, path, counts, expected_revision, source_map):
    report = read(case / path)
    require(report['counts'] == counts, 'raw counts ' + path)
    observed = Counter(item['status'] for item in report['findings'])
    require({key: observed[key] for key in counts} == counts and set(observed) <= set(counts),
            'counts from saved findings ' + path)
    require(report['revision'] == expected_revision, 'raw revision ' + path)
    label = 'parent' if 'parent' in path else ('fix' if case.name == 'ocfs2' else 'fixed')
    for entry in report['files_read']:
        matches = [x for p, x in source_map.items() if label in p.relative_to(case).parts and
                   x.get('path', x.get('source_path')) == entry['path']]
        require(len(matches) == 1 and matches[0]['sha256'] == entry['sha256'], 'raw input binding')
    return report


def verify(require_freeze=True):
    locked = check(read(HERE / 'freeze_manifest.json')['files']) if require_freeze else []
    for name, digest in PRIOR_LOCKS.items():
        require(sha(PRIOR / name) == digest, 'prior anchor ' + name)
    prior = read(PRIOR / 'completion_manifest.json')
    old = {'previous_stage': check(prior['verified_new_files'])}
    for name, records in prior['prior_record_groups'].items():
        old[name] = check(records)
    require(len(old['previous_stage']) == 64 and [len(x) for x in prior['prior_record_groups'].values()] ==
            [32, 46, 55, 27, 4], 'prior record groups')
    require(prior['verified_new_files'] == read(PRIOR / 'freeze_manifest.json')['files'], 'prior binding')
    require(sha(HERE / 'protocol_pre.md') == PROTOCOL, 'formal protocol identity')
    for filename, digest in TOOLS.items():
        require(sha(RULES / filename) == digest, 'original tool modified')

    audit = read(HERE / 'audit/final_audit.json')
    require(not audit['blockers_found'] and audit['checks'] and all(audit['checks'].values()),
            'independent final audit')
    for filename, digest in audit['final_inputs_sha256'].items():
        path = (HERE / filename.replace('\\', '/')).resolve()
        require(path.is_relative_to(RULES.resolve()) and sha(path) == digest, 'audited input ' + filename)

    oc = HERE / 'ocfs2'
    pwm = HERE / 'pwm'
    oc_facts = read(oc / 'facts.json')
    pwm_facts = read(pwm / 'facts.json')
    oc_sources = sources(oc, ['source_manifest.json'])
    pwm_sources = sources(pwm, ['source_manifest.json', 'source_extension_manifest.json',
                                'type_contract_manifest.json'])
    excerpt_counts = {name: quotations(case, facts, source_map) for name, case, facts, source_map in (
        ('ocfs2', oc, oc_facts, oc_sources), ('pwm', pwm, pwm_facts, pwm_sources))}

    expected = {
        'ocfs2': [('parent', 'parent.json', dict(candidate=3, normal=10, insufficient=0),
                   'c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4^'),
                  ('fix', 'fix.json', dict(candidate=0, normal=13, insufficient=0),
                   'c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4')],
        'pwm': [('parent', 'parent.json', dict(candidate=1, normal=2, insufficient=0),
                 'd7b4408374b69dbc246c59c29e3077920b9f03eb'),
                ('fixed', 'fixed.json', dict(candidate=0, normal=3, insufficient=0),
                 '09f688f0718f57f9cf68ee1aa94490f641e759ba')],
    }
    reports = {}
    for name, case, source_map in (('ocfs2', oc, oc_sources), ('pwm', pwm, pwm_sources)):
        for label, filename, counts, revision in expected[name]:
            reports[(name, label)] = raw_report(case, 'raw/' + filename, counts, revision, source_map)
    replay = read(oc / 'replay.json')
    for label, entry in replay['results'].items():
        raw = reports[('ocfs2', label)]
        require(sha(safe(oc, entry['raw_output'])) == entry['raw_output_sha256'], 'ocfs2 raw SHA')
        primary = [x for x in raw['findings'] if x['function'] == 'ocfs2_dinode_has_extents' and
                   x['field'] == 'i_flags']
        require(len(primary) == 1 and primary[0]['status'] == ('candidate' if label == 'parent' else 'normal')
                and primary[0] == entry['primary'], 'ocfs2 primary binding')
        require(all(x in raw['findings'] for x in entry['normal_control_reads']), 'ocfs2 normal controls')
    pwm_replay = read(pwm / 'replay_manifest.json')
    for label, entry in pwm_replay['results'].items():
        raw = reports[('pwm', label)]
        require(sha(safe(pwm, entry['raw_path'])) == entry['sha256'] and entry['counts'] == raw['counts'],
                'PWM raw SHA/count binding')
        primary = [x for x in raw['findings'] if x['function'] == 'raspberrypi_pwm_get_property' and
                   x['field'] == 'reg']
        require(len(primary) == 1 and primary[0]['status'] == ('candidate' if label == 'parent' else 'normal'),
                'PWM primary binding')
        require(len([x for x in raw['findings'] if x['function'] == 'raspberrypi_pwm_set_property' and
                     x['status'] == 'normal']) == 2, 'PWM set controls')

    oc_before = read(oc / 'tool_before_replay.json')
    oc_after = read(oc / 'tool_after_replay.json')
    require(oc_before == oc_after and oc_before['script_sha256'] == TOOLS['endian_consumer_single_revision.py']
            and oc_before['protocol_sha256'] == PROTOCOL, 'ocfs2 direct-import snapshot equality')
    require(not oc_before['kernel_execution'] and not oc_before['compilation'], 'ocfs2 execution scope')
    for prefix in ('prepare', 'replay', 'extension', 'type_contract'):
        before = read(pwm / (prefix + '_hashes_before.json'))['files']
        after = read(pwm / (prefix + '_hashes_after.json'))['files']
        require(before == after, 'PWM provenance before/after ' + prefix)
        for filename, item in before.items():
            path = Path(item['absolute_path']) if 'absolute_path' in item else safe(pwm, filename)
            require(path.is_relative_to(RULES.resolve()) and sha(path) == item['sha256'], 'PWM saved dependency')

    # Bind the zero-value boundary directly to saved parent source, without a
    # synthetic nonzero input or a model-provided value.
    pwm_parent = pwm / 'source/parent/drivers/pwm/pwm-raspberrypi-poe.c'
    text = pwm_parent.read_text(encoding='utf-8')
    require('#define RPI_PWM_CUR_DUTY_REG\t\t0x0' in text, 'PWM current-duty constant')
    require('raspberrypi_pwm_get_property(rpipwm->firmware, RPI_PWM_CUR_DUTY_REG,' in text,
            'PWM actual caller constant')
    require(text.count('raspberrypi_pwm_get_property(') == 2, 'PWM definition plus one local call')
    # Equation only; not a new architecture execution.
    require((0).to_bytes(4, 'little') == (0).to_bytes(4, 'big'), 'zero is representation invariant')
    require(oc_facts['identity']['new_case_count'] == 0 and
            oc_facts['identity']['blind_validation'] is False, 'known ocfs2 scope')
    require(pwm_facts['experiment_kind'].startswith('already-read') and
            not pwm_facts['proof_flags']['runtime_bug_demonstrated'] and
            not pwm_facts['proof_flags']['request_bytes_differ_for_observed_local_zero_domain'],
            'PWM known-case and no current-byte-mismatch scope')
    for label in ('parent', 'fixed'):
        binding = pwm_facts['primary'][label]
        require(binding['automatic_fact'] in reports[('pwm', label)]['findings'] and
                binding['human_binding']['source_visible_value_domain'] == [0], 'PWM facts/raw/value binding')
        require(all(x in reports[('pwm', label)]['findings'] for x in pwm_facts['normal_controls'][label]),
                'PWM facts normal binding')

    case_locks = {}
    for case in (oc, pwm):
        manifest = read(case / 'artifact_manifest.json')
        for entry in manifest['files']:
            path = safe(case, entry['path'])
            require(sha(path) == entry['sha256'], 'case artifact lock ' + str(path))
        case_locks[case.name] = len(manifest['files'])

    cmd_counts = {
        'ocfs2': commands(oc, ['commands.json']),
        'pwm': commands(pwm, ['commands_prepare.json', 'commands_replay.json',
                             'commands_source_extension.json', 'commands_type_contract.json']),
    }
    return dict(saved_at_utc=datetime.now(timezone.utc).isoformat(),
        conclusion='Known cross-subsystem facts are bound to saved source and reviewed consumers; no generalization claim.',
        verified_new_files=locked, prior_record_groups=old,
        saved_source_files=dict(ocfs2=len(oc_sources), pwm=len(pwm_sources)),
        literal_quotations=excerpt_counts, command_records=cmd_counts,
        case_artifact_records=case_locks,
        interface_inventories=2, independent_holdout_executions=0, new_confirmed_cases=0,
        selected_12_classification=[6, 5, 1], pwm_current_caller_value=0,
        pwm_current_request_byte_mismatch_established=False,
        ocfs2_actual_big_endian_io_established=False, kernel_execution=False, compilation=False,
        external_model_calls=0, general_detector_established=False,
        audit_file_sha256=sha(HERE / 'audit/final_audit.json'),
        limits='Manual callers/value/config facts; regex rules, local format authority, no actual device or independent positive.')


def freeze():
    files = {path.resolve() for path in HERE.rglob('*') if path.is_file() and '__pycache__' not in path.parts
             and path.name not in ('freeze_manifest.json', 'completion_manifest.json')}
    files.update((RULES / name).resolve() for name in TOOLS)
    files.update((PRIOR / name).resolve() for name in PRIOR_LOCKS)
    save_once(HERE / 'freeze_manifest.json', dict(
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Post-development known cross-subsystem source/facts lock, not a blind holdout.',
        dependencies='Original two rule files explicitly locked; saved WSL direct-import snapshots only, not binary closure.',
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
    print('verified:', len(result['verified_new_files']), 'locked records;',
          result['saved_source_files'], 'saved sources;', result['literal_quotations'], 'literal quotations;',
          '2 known interfaces, 0 independent holdouts, 0 new confirmed cases')


if __name__ == '__main__':
    main()
