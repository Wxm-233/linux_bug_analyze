"""Freeze metadata before new source; export only four bounded parent shapes."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
POOL = BASE / 'bounded_interface_holdout_20261003/pool_metadata.json'
DEPENDENCIES = [BASE / 'interface_facts_20261008/interface_fact_extractor.py',
                BASE / 'endian_consumer_single_revision.py',
                BASE / 'interface_facts_20261008/closeout_manifest.json']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    p = HERE / name
    if p.exists():
        raise RuntimeError('Refusing overwrite: ' + str(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def freeze():
    records = json.loads(POOL.read_text(encoding='utf-8'))['pools']['fs']
    assert len(records) == 32
    audit = json.loads((HERE / 'exposure_audit.json').read_text(encoding='utf-8'))
    excluded = {r['commit'] for r in audit['source_exposed']}
    metadata = [dict(order=i, commit=r['commit'], parents=r['parents'], subject=r['subject'],
                     previous_metadata_selection_status=r.get('selection_status'),
                     exposure='prior_source_evidence' if r['commit'] in excluded else
                              'metadata_seen_no_prior_source_evidence_in_defined_audit')
                for i, r in enumerate(records, 1)]
    queue = [r for r in metadata if r['commit'] not in excluded and
             re.search(r'\b(?:fix|fixes|missed)\b', r['subject'], re.I)][:4]
    save('metadata_snapshot.json', dict(pool_count=32, records=metadata, queue=queue))
    files = [HERE / 'protocol_pre.md', HERE / 'exposure_audit.json', HERE / 'prepare.py',
             HERE / 'metadata_snapshot.json', POOL, *DEPENDENCIES]
    save('freeze_metadata_pre.json', dict(time_utc=datetime.now(timezone.utc).isoformat(),
         files=[dict(path=str(p), sha256=sha(p)) for p in files],
         selected_queue_commits=[r['commit'] for r in queue],
         parent_exports_before_freeze=0, extractor_runs_before_freeze=0, patches_read_before_freeze=0))
    print(json.dumps(dict(metadata=32, parent_queue=[r['commit'] for r in queue],
                         freeze_sha256=sha(HERE / 'freeze_metadata_pre.json'))))


def git_capture(folder, label, args, commands):
    argv = ['wsl', '-d', 'Ubuntu', '--', 'git', '-C', '/root/repos/linux', *args]
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = folder / (label + '.stdout.bin'), folder / (label + '.stderr.bin')
    out.write_bytes(p.stdout)
    err.write_bytes(p.stderr)
    commands.append(dict(argv=argv, returncode=p.returncode,
                         stdout=str(out), stdout_sha256=sha(out),
                         stderr=str(err), stderr_sha256=sha(err)))
    if p.returncode:
        raise RuntimeError('git failed: ' + label)
    return p.stdout


def export():
    locked = json.loads((HERE / 'freeze_metadata_pre.json').read_text(encoding='utf-8'))
    for r in locked['files']:
        assert sha(Path(r['path'])) == r['sha256'], r['path']
    assert not (HERE / 'parent_resume_sources.json').exists()
    meta = json.loads((HERE / 'metadata_snapshot.json').read_text(encoding='utf-8'))
    commands, observations = [], []
    try:
        for r in meta['queue']:
            folder = HERE / 'prescreen_resume' / r['commit'][:12]
            folder.mkdir(parents=True, exist_ok=False)
            parents = git_capture(folder, 'parents', ['show', '-s', '--format=%P', r['commit']], commands).decode().split()
            assert parents == r['parents'] and len(parents) == 1
            parent = parents[0]
            paths = git_capture(folder, 'path_names', ['diff-tree', '--no-commit-id', '--name-only', '-r', r['commit']], commands).decode().splitlines()
            choices = sorted(p for p in paths if p.startswith('fs/') and p.endswith('.c'))
            row = dict(r, revision=parent, changed_path_names=paths, sources=[],
                       exposure='parent_source_prescreen_exposed', fixed_or_patch_exported=False)
            if not choices:
                row['export_status'] = 'no_fs_c_file'
                observations.append(row)
                continue
            path = choices[0]
            raw = git_capture(folder, 'parent_c', ['show', parent + ':' + path], commands)
            names = [path]
            quoted = re.findall(rb'^\s*#\s*include\s*"([^"\n]+)"', raw, re.M)[:2]
            names += [posixpath.normpath(str(PurePosixPath(path).parent / x.decode())) for x in quoted]
            for i, source_path in enumerate(names):
                payload = raw if i == 0 else git_capture(folder, 'parent_header_' + str(i), ['show', parent + ':' + source_path], commands)
                blob = git_capture(folder, 'blob_' + str(i), ['rev-parse', parent + ':' + source_path], commands).decode().strip()
                calculated = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
                assert blob == calculated
                saved = folder / ('source_' + str(i) + PurePosixPath(source_path).suffix)
                saved.write_bytes(payload)
                row['sources'].append(dict(revision=parent, source_path=source_path, saved_path=str(saved),
                                           blob_sha1=blob, sha256=sha(saved), byte_count=len(payload)))
            row['export_status'] = 'ok'
            observations.append(row)
    finally:
        save('parent_resume_commands.json', commands)
        save('parent_resume_sources.json', dict(parent_prescreens=len(observations), observations=observations,
                                        extractor_executions=0, patches_exported=0))
    print(json.dumps(dict(parent_prescreens=len(observations), source_files=sum(len(r['sources']) for r in observations),
                         extractor_executions=0, patches_exported=0)))


if __name__ == '__main__':
    {'freeze': freeze, 'export': export}[sys.argv[1]]()
