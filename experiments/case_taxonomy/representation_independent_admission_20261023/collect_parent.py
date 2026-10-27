"""Local Git blobs only; fixed parent paths and no implicit object fetch."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent


def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def git(arguments):
    argv = ['git', '-C', '/root/repos/linux', *arguments]
    done = subprocess.run(argv, capture_output=True, timeout=30,
                          env=dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0'))
    if done.returncode:
        raise RuntimeError({'argv': argv, 'returncode': done.returncode,
                            'stderr': done.stderr.decode('utf-8', errors='replace')})
    return argv, done.stdout, done.stderr.decode('utf-8', errors='replace')


def main(action):
    selection = json.loads((HERE / 'selection_pre.json').read_text(encoding='utf-8'))
    revision = selection['selected']['parents'][0]
    paths = selection['parent_paths']
    assert len(paths) == len(set(paths)) == 8
    if action == 'plan':
        argv, raw, stderr = git(['ls-tree', '-r', '--name-only', revision, '--', *paths])
        available = raw.decode('utf-8').splitlines()
        missing = sorted(set(paths) - set(available))
        result = {'task': 'N2.27', 'revision': revision, 'paths': paths,
                  'selection_sha256': hashlib.sha256((HERE / 'selection_pre.json').read_bytes()).hexdigest(),
                  'availability_argv': argv, 'availability_stderr': stderr,
                  'missing_paths': missing, 'status': 'ready' if not missing else 'insufficient',
                  'new_source_body_reads': 0}
        save('source_plan.json', result)
        print(json.dumps({'status': result['status'], 'named_paths': len(paths), 'missing': missing}))
        return
    gate = (HERE / 'pre_collection_review.md').read_text(encoding='utf-8')
    assert 'PARENT_COLLECTION_GATE: PASS' in gate
    plan = json.loads((HERE / 'source_plan.json').read_text(encoding='utf-8'))
    assert plan['status'] == 'ready' and plan['revision'] == revision and plan['paths'] == paths
    assert plan['selection_sha256'] == hashlib.sha256((HERE / 'selection_pre.json').read_bytes()).hexdigest()
    assert not (HERE / 'source_manifest.json').exists()
    destination = HERE / 'parent_sources'
    destination.mkdir(exist_ok=False)
    result = {'task': 'N2.27', 'revision': revision, 'status': 'collecting', 'files': [],
              'source_plan_sha256': hashlib.sha256((HERE / 'source_plan.json').read_bytes()).hexdigest(),
              'new_fix_or_commit_body_reads': 0, 'new_builds': 0, 'new_boots': 0, 'paid_model_requests': 0}
    try:
        for path in paths:
            argv, raw, stderr = git(['show', revision + ':' + path])
            out = destination / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(raw)
            result['files'].append({'path': path, 'revision': revision, 'artifact': str(out.relative_to(HERE)),
                                    'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                                    'argv': argv, 'stderr': stderr})
        result['status'] = 'collected'
    except Exception as error:
        result.update(status='stopped', error=repr(error))
        save('source_manifest.json', result)
        raise
    save('source_manifest.json', result)
    print(json.dumps({'status': result['status'], 'complete_parent_files': len(result['files'])}))


if __name__ == '__main__':
    assert os.name == 'posix', 'use existing WSL repository'
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['plan', 'collect'])
    main(parser.parse_args().action)
