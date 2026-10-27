"""Exact-parent Git file collection after the raw-input adapter is fixed."""
from pathlib import Path, PurePosixPath
import base64
import argparse
import hashlib
import json
import re
import subprocess

STAGE = Path(__file__).resolve().parent
OLD = STAGE.parent / 'core_consumer_qualification_20261017'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan-only', action='store_true', help='Metadata plan only, no source-body reads')
    args = parser.parse_args()
    baseline = STAGE / 'adapter_baseline.json'
    if (STAGE / 'initial_sources.json').exists():
        raise RuntimeError('preserve first source collection')
    selection = json.loads((STAGE / 'selection.json').read_text(encoding='utf-8'))
    rules = json.loads((OLD / 'protocol_pre.json').read_text(encoding='utf-8'))
    queues = {q['name']: q for q in rules['queues_in_order']}
    plan = []
    for index, candidate in enumerate(selection['candidates']):
        case = candidate.get('case') or candidate.get('id') or ('E' if index == 0 else 'F')
        queue = queues[candidate['queue']]
        parent = candidate.get('parent') or candidate['parents'][0]
        assert re.fullmatch('[0-9a-f]{40}', parent)
        paths = candidate['matched_paths']
        implementation = [p for p in queue['implementation_paths'] if p in paths][:2]
        headers = [p for p in queue['header_paths'] if p in paths]
        headers += [p for p in queue['header_paths'] if p not in headers]
        chosen = implementation + headers[:2]
        assert len(chosen) <= 4
        plan.append({'case': case, 'hash': candidate['hash'], 'parent': parent,
                     'queue': candidate['queue'], 'paths': chosen})
    plan_record = {
        'selection_sha256': sha((STAGE / 'selection.json').read_bytes()),
        'prior_queue_rules_sha256': sha((OLD / 'protocol_pre.json').read_bytes()), 'cases': plan,
        'selection_rule': 'matched registered implementations, then matched headers and remaining registered header order; no title/outcome selection'
    }
    plan_path = STAGE / 'initial_material_plan.json'
    if plan_path.exists():
        if json.loads(plan_path.read_text(encoding='utf-8')) != plan_record:
            raise RuntimeError('metadata plan changed; preserve first plan')
    else:
        plan_path.write_text(json.dumps(plan_record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.plan_only:
        print(json.dumps({'status': 'metadata_plan_only', 'cases': plan}))
        return
    if not baseline.is_file():
        raise RuntimeError('adapter baseline required before reading new parent bodies')
    rows = []
    for item in plan:
        for path in item['paths']:
            pure = PurePosixPath(path)
            assert not pure.is_absolute() and '..' not in pure.parts
            argv = ['git', '-C', '/root/repos/linux', 'show', item['parent'] + ':' + path]
            proc = subprocess.run(argv, capture_output=True, timeout=30)
            row = {'id': item['case'] + ':' + path, 'case': item['case'],
                   'material_group': item['case'] + '_parent', 'revision': item['parent'],
                   'path': path, 'status': 'collection_error', 'argv': argv,
                   'exit_code': proc.returncode}
            if proc.returncode:
                row['error'] = proc.stderr.decode('utf-8', errors='replace')[:1500]
            else:
                row.update(sha256=sha(proc.stdout), bytes=len(proc.stdout))
                try:
                    row.update(text=proc.stdout.decode('utf-8'), status='collected')
                except UnicodeDecodeError:
                    row.update(raw_base64=base64.b64encode(proc.stdout).decode(), status='non_utf8_source')
            rows.append(row)
    result = {'protocol_sha256': sha((STAGE / 'protocol_pre.json').read_bytes()),
              'adapter_baseline_sha256': sha(baseline.read_bytes()),
              'material_plan_sha256': sha((STAGE / 'initial_material_plan.json').read_bytes()),
              'semantic_layer': 'unpreprocessed_original_parent_source', 'documents': rows,
              'new_child_messages_or_patches_read': 0, 'network_requests': 0}
    (STAGE / 'initial_sources.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(rows), 'collected': sum(r['status'] == 'collected' for r in rows),
                      'bytes': sum(r.get('bytes', 0) for r in rows), 'cases': [p['case'] for p in plan]}))

if __name__ == '__main__':
    main()
