"""Run only frozen parent queries; patch access is a separate gated phase."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import traceback
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(HERE))
from prepare_export_resume import sha, save, git_capture

RULE = BASE / 'interface_facts_20261008/interface_fact_extractor.py'
HELPER = BASE / 'endian_consumer_single_revision.py'


def load(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def check(lock):
    for r in lock['files']:
        assert sha(Path(r['path'])) == r['sha256'], r['path']


def lock():
    check(load('freeze_metadata_pre.json'))
    e = load('export_erratum_pre.json')
    assert sha(HERE / 'prepare_export_resume.py') == e['resume_runner_sha256']
    selected = load('selection_pre.json')
    assert len(selected['queries']) <= 2
    assert selected['parent_prescreen_count'] <= 4
    files = [HERE / n for n in ['protocol_pre.md', 'selection_pre.json', 'parent_resume_sources.json',
                               'parent_resume_commands.json', 'freeze_metadata_pre.json',
                               'export_erratum_pre.json', 'run_selected.py', 'prepare_export_resume.py']]
    files += [RULE, HELPER]
    for obs in load('parent_resume_sources.json')['observations']:
        for s in obs['sources']:
            p = Path(s['saved_path'])
            assert sha(p) == s['sha256']
            assert hashlib.sha1(b'blob ' + str(len(p.read_bytes())).encode() + b'\0' + p.read_bytes()).hexdigest() == s['blob_sha1']
            files.append(p)
    save('freeze_queries_pre.json', dict(time_utc=datetime.now(timezone.utc).isoformat(),
         files=[dict(path=str(p), sha256=sha(p)) for p in files],
         extractor_executions_before_lock=0, patches_read_before_lock=0))
    print(json.dumps(dict(queries=len(selected['queries']), freeze_sha256=sha(HERE/'freeze_queries_pre.json'))))


def rule_module():
    spec = importlib.util.spec_from_file_location('frozen_interface_facts', RULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parent():
    check(load('freeze_queries_pre.json'))
    assert not (HERE/'parent_results.json').exists()
    mod = rule_module()
    sources = {s['saved_path']: s for r in load('parent_resume_sources.json')['observations'] for s in r['sources']}
    outputs, executed = [], 0
    for q in load('selection_pre.json')['queries']:
        def source(key):
            r = sources[q[key]]
            return mod.Source(r['source_path'], r['revision'], r['saved_path'], r['blob_sha1'], Path(r['saved_path']).read_bytes())
        executed += 1
        try:
            values = mod.scalar_reads(source('source'), source('declaration_source'), q['function'], q['object'], q['structure'], q['field'])
            outputs.append(dict(query=q['id'], execution_status='ok', outputs=values))
        except Exception as error:
            outputs.append(dict(query=q['id'], execution_status='error', exception_type=type(error).__name__,
                                message=str(error), traceback=traceback.format_exc()))
    check(load('freeze_queries_pre.json'))
    save('parent_results.json', dict(executions=executed, outputs=outputs))
    save('parent_output_lock.json', dict(time_utc=datetime.now(timezone.utc).isoformat(),
         parent_results_sha256=sha(HERE/'parent_results.json'),
         query_freeze_sha256=sha(HERE/'freeze_queries_pre.json'),
         rule_sha256=sha(RULE), source_prescreens=load('selection_pre.json')['parent_prescreen_count'],
         patches_read_before_output_lock=0))
    print(json.dumps(dict(executions=executed, results_sha256=sha(HERE/'parent_results.json'))))


def unseal():
    check(load('freeze_queries_pre.json'))
    assert sha(HERE/'parent_results.json') == load('parent_output_lock.json')['parent_results_sha256']
    assert not (HERE/'unseal_manifest.json').exists()
    selected = load('selection_pre.json')
    assert selected['queries'], 'No selected input: no patch access allowed'
    commits = dict.fromkeys(q['commit'] for q in selected['queries'])
    old = {r['commit']: r for r in load('parent_resume_sources.json')['observations']}
    commands, rows = [], []
    for commit in commits:
        folder = HERE/'post_review'/commit[:12]
        folder.mkdir(parents=True, exist_ok=False)
        git_capture(folder, 'commit_message', ['show', '-s', '--format=%H%n%P%n%aI%n%cI%n%B', commit], commands)
        path = old[commit]['sources'][0]['source_path']
        git_capture(folder, 'selected_file_patch', ['diff', old[commit]['revision'], commit, '--', path], commands)
        current = []
        for i, s in enumerate(old[commit]['sources']):
            payload = git_capture(folder, 'fixed_source_'+str(i), ['show', commit+':'+s['source_path']], commands)
            blob = git_capture(folder, 'fixed_blob_'+str(i), ['rev-parse', commit+':'+s['source_path']], commands).decode().strip()
            assert hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest() == blob
            saved = folder/('fixed_'+str(i)+Path(s['source_path']).suffix)
            saved.write_bytes(payload)
            current.append(dict(revision=commit, source_path=s['source_path'], saved_path=str(saved), blob_sha1=blob, sha256=sha(saved)))
        rows.append(dict(commit=commit, parent=old[commit]['revision'], sources=current))
    save('unseal_commands.json', commands)
    save('unseal_manifest.json', dict(time_utc=datetime.now(timezone.utc).isoformat(),
         output_lock_sha256=sha(HERE/'parent_output_lock.json'), observations=rows))
    print(json.dumps(dict(unsealed_inputs=len(rows), fixed_source_files=sum(len(r['sources']) for r in rows))))


def fixed():
    # Post-unseal comparison of the identical query; never an independent control.
    check(load('freeze_queries_pre.json'))
    mod = rule_module()
    rows = {r['commit']:r for r in load('unseal_manifest.json')['observations']}
    prior = {s['saved_path']:s for r in load('parent_resume_sources.json')['observations'] for s in r['sources']}
    outputs = []
    for q in load('selection_pre.json')['queries']:
        def source(key):
            path = prior[q[key]]['source_path']
            s = next(s for s in rows[q['commit']]['sources'] if s['source_path'] == path)
            assert sha(Path(s['saved_path'])) == s['sha256']
            return mod.Source(s['source_path'], s['revision'], s['saved_path'], s['blob_sha1'], Path(s['saved_path']).read_bytes())
        try:
            values=mod.scalar_reads(source('source'),source('declaration_source'),q['function'],q['object'],q['structure'],q['field'])
            outputs.append(dict(query=q['id'], execution_status='ok', outputs=values))
        except Exception as error:
            outputs.append(dict(query=q['id'], execution_status='error', exception_type=type(error).__name__, message=str(error)))
    save('fixed_results.json', dict(post_unseal_only=True, independent_control=False, outputs=outputs))
    print(json.dumps(dict(post_unseal_queries=len(outputs))))


if __name__ == '__main__':
    {'lock':lock,'parent':parent,'unseal':unseal,'fixed':fixed}[sys.argv[1]]()
