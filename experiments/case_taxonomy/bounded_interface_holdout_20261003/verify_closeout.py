"""Saved-record checks only; no rule, Git, model, compiler or kernel execution."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES = HERE.parent
PRIOR = RULES / 'cross_subsystem_facts_20261003'
ANCHORS = {'freeze_manifest.json': '4590750847754dc0ea49d6cb64f442682a2d554de1deedae0050f1263d39433b',
           'completion_manifest.json': 'c88db1ee29e1d7542c780bd76bfdc13f07b12782db4b2f861c6761276f267867'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(relative):
    path = (HERE / relative.replace('\\', '/')).resolve()
    require(path.is_relative_to(RULES.resolve()), 'path escapes case_taxonomy')
    return path


def lock(filename):
    value = read(HERE / filename)
    for item in value['files']:
        require(sha(safe(item['path'])) == item['sha256'], 'lock mismatch ' + item['path'])
    return value


def save_once(path, obj):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for child in obj.values():
            yield from walk(child)
    elif isinstance(obj, list):
        for child in obj:
            yield from walk(child)


def verify(frozen=True, reviewed=True):
    current = lock('freeze_final.json')['files'] if frozen else []
    for name, digest in ANCHORS.items():
        require(sha(PRIOR / name) == digest, 'prior stage anchor')
    prior = read(PRIOR / 'completion_manifest.json')
    prior_files = prior['verified_new_files']
    prior_groups = prior['prior_record_groups']
    for entries in [prior_files, *prior_groups.values()]:
        for item in entries:
            path = (RULES / item['path']).resolve()
            require(path.is_relative_to(RULES.resolve()) and sha(path) == item['sha256'], 'prior file modified')
    require(len(prior_files) == 742, 'prior scientific lock count')
    pre = lock('freeze_pre.json')
    gate = lock('execution_gate_lock_pre.json')
    parents = lock('parents_lock.json')
    choice = read(HERE / 'selection.json')['selected']
    pool = read(HERE / 'pool_metadata.json')
    require(0 < len(choice) <= 2 and pool['count'] <= 64 and
            all(len(entries) <= 32 for entries in pool['pools'].values()), 'finite selection/pool')
    require(pre['source_or_patch_read_before_seal'] is False and parents['patch_unsealed'] is False,
            'pre-exposure stage scope')
    require(pre['sealed_at_utc'] <= gate['sealed_at_utc'] <= read(HERE / 'parents_started.json')['started_at_utc']
            <= parents['sealed_at_utc'] <= read(HERE / 'unseal_authorization.json')['authorized_at_utc'],
            'pre/gate/parent/unseal order')
    require(parents['pre_freeze_sha256'] == sha(HERE / 'freeze_pre.json'), 'parent/pre binding')
    authorization = read(HERE / 'unseal_authorization.json')
    require(authorization['allowed'] and authorization['all_parent_returncodes_zero'] and
            authorization['parent_lock_sha256'] == sha(HERE / 'parents_lock.json'), 'unseal gate')

    commands = {}
    for phase in ('prepare_complete', 'parents', 'unseal'):
        commands[phase] = read(HERE / ('commands_' + phase + '.json'))
        for item in commands[phase]:
            for stream in ('stdout', 'stderr'):
                require(sha(safe(item[stream])) == item[stream + '_sha256'], 'command stream SHA')
            if phase != 'prepare_complete':
                require(item['returncode'] == 0, 'formal rule/source command failure')
    require(len(commands['parents']) == len(choice), 'one parent CLI per selected input')
    require(all(c['started_at_utc'] >= parents['sealed_at_utc'] for c in commands['unseal']),
            'no unseal command precedes parent lock')
    for item in commands['prepare_complete']:
        argv = item['argv']
        require(not (argv[0] == 'git' and argv[1] == 'show') and
                not any('endian_' in x and x.endswith('.py') for x in argv), 'metadata phase only')

    manifest = read(HERE / 'source_manifest.json')
    source_map = {}
    for item in manifest:
        path = safe(item['saved_path'])
        raw = path.read_bytes()
        require(sha(path) == item['sha256'] and len(raw) == item['bytes'] and
                hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['blob_sha1'],
                'saved source/blob binding')
        source_map[(item['role'], item['label'], item['source_path'])] = item

    rows = []
    for selected in choice:
        role = selected['role']
        membership = [x for x in pool['pools'][selected['channel']] if x['commit'] == selected['commit']]
        require(len(membership) == 1 and membership[0]['selection_status'] == 'selected' and
                not membership[0]['prior_record_matches'] and not selected['preassigned_positive_label'],
                'selection/exposure record binding')
        for label, revision in (('parent', selected['parent']), ('fixed', selected['commit'])):
            path = HERE / role / 'raw' / (label + '.json')
            raw = read(path)
            require(raw['revision'] == revision and raw['source_file'] == selected['source_file'], 'raw identity')
            observed = Counter(item['status'] for item in raw['findings'])
            require(raw['counts'] == {name: observed[name] for name in ('candidate', 'normal', 'insufficient')},
                    'raw findings/counts')
            for entry in raw['files_read']:
                original = source_map[(role, label, entry['path'])]
                require(original['sha256'] == entry['sha256'] and original['revision'] == revision,
                        'raw same-version input identity')
            rows.append(dict(role=role, version=label, counts=raw['counts'], raw_sha256=sha(path)))
        saved = [x for x in parents['summaries'] if x['role'] == role]
        require(len(saved) == 1 and saved[0]['returncode'] == 0 and
                saved[0]['raw_sha256'] == sha(HERE / role / 'raw/parent.json'), 'parent lock exact raw')

    audit_hash = None
    extra_sources, quotations = 0, 0
    if reviewed:
        bound_sources = {safe(item['saved_path']): item for item in manifest}
        for selected in choice:
            role = selected['role']
            leaf = HERE / role / 'manual_review'
            extra = read(leaf / 'source_manifest_extra.json')
            require(len(extra) <= 8, 'finite additional manual source scope')
            for item in extra:
                path = safe(item['saved_path'])
                raw = path.read_bytes()
                require(sha(path) == item['sha256'] and
                        hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['blob_sha1'],
                        'manual same-version source/blob')
                bound_sources[path] = item
                extra_sources += 1
            found_quotes = 0
            for entry in walk(read(leaf / 'review.json')):
                if not {'saved_path', 'start_line', 'end_line', 'text', 'sha256', 'blob_sha1'}.issubset(entry):
                    continue
                path = safe(entry['saved_path'])
                require(path in bound_sources, 'manual quote not bound')
                source = bound_sources[path]
                require(source['sha256'] == entry['sha256'] and source['blob_sha1'] == entry['blob_sha1'] and
                        source['revision'] == entry['revision'] and source['source_path'] == entry['source_path'],
                        'manual quote/source identity')
                lines = path.read_text(encoding='utf-8').splitlines()
                require(1 <= entry['start_line'] <= entry['end_line'] <= len(lines) and
                        '\n'.join(lines[entry['start_line']-1:entry['end_line']]) == entry['text'],
                        'literal manual quote')
                found_quotes += 1
            require(found_quotes > 0, 'manual review quotes missing')
            quotations += found_quotes
        audit = read(HERE / 'audit_final/final_audit.json')
        require(audit['checks'] and all(audit['checks'].values()) and not audit['blockers_found'],
                'independent final method audit')
        for name, digest in audit['final_inputs_sha256'].items():
            require(sha(safe(name)) == digest, 'audited final input')
        audit_hash = sha(HERE / 'audit_final/final_audit.json')
        require(read(HERE / 'review_summary.json')['new_confirmed_cases'] == 0,
                'no automatic case promotion')
    return dict(verified_at_utc=datetime.now(timezone.utc).isoformat(), verified_new_files=current,
        previous_stage_files=prior_files, previous_record_groups=prior_groups,
        metadata_pool_size=pool['count'], selected_inputs=len(choice), original_cli_observations=rows,
        saved_tool_source_files=len(manifest), new_confirmed_cases=0,
        extra_manual_source_records=extra_sources, literal_manual_quotations=quotations,
        selected_12_classification=[6, 5, 1], model_calls=0, compilation=False, kernel_execution=False,
        generalization_accuracy_established=False, final_method_audit_sha256=audit_hash,
        limits='Purposeful metadata-informed pair; new only within scanned records; manual source review after unseal.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-execution', action='store_true')
    parser.add_argument('--check-unfrozen', action='store_true')
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    require(sum((args.check_execution, args.check_unfrozen, args.freeze)) <= 1, 'choose one mode')
    if args.freeze:
        verify(frozen=False)
        files = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and
                 p.name not in ('freeze_final.json', 'completion_manifest.json')]
        save_once(HERE / 'freeze_final.json', dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
            scope='Post-review closeout lock; original pre-parent freeze remains intact.',
            files=[dict(path=p.relative_to(HERE).as_posix(), sha256=sha(p)) for p in sorted(files)]))
    result = verify(frozen=not (args.check_execution or args.check_unfrozen), reviewed=not args.check_execution)
    if args.freeze:
        save_once(HERE / 'completion_manifest.json', result)
    print(json.dumps({k: result[k] for k in ('metadata_pool_size', 'selected_inputs',
        'original_cli_observations', 'saved_tool_source_files', 'new_confirmed_cases')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
