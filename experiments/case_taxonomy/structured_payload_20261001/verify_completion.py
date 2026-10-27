"""Verify frozen rules/raw evidence and preserved older versions at closeout."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
RULES = HERE.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    destination = HERE/'completion_manifest.json'
    if destination.exists():
        raise RuntimeError('refusing to overwrite completion snapshot')
    verified = []
    for freeze_dir in (HERE, RULES/'outbound_scalar_20260930'):
        freeze = json.loads((freeze_dir/'freeze_manifest.json').read_text(encoding='utf-8'))
        for record in freeze['files']:
            path = RULES/record['path']
            if sha(path) != record['sha256']:
                raise RuntimeError('frozen file changed: '+record['path'])
            verified.append(dict(path=record['path'], sha256=record['sha256'],
                                 freeze=freeze_dir.name))
    reports = []
    for name in ('parent_manifest_pre_review.json', 'fix_manifest_post_review.json'):
        manifest_path = HERE/'holdout'/name
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['freeze_sha256'] != sha(HERE/'freeze_manifest.json'):
            raise RuntimeError('raw manifest/freeze mismatch')
        for record in manifest['records']:
            path = manifest_path.parent/record['output']
            if sha(path) != record['sha256']:
                raise RuntimeError('raw output changed: '+record['output'])
            reports.append(dict(path=path.relative_to(RULES).as_posix(), sha256=sha(path)))
    development = json.loads((HERE/'development/known_replay_summary.json').read_text(encoding='utf-8'))
    if development['module_sha256'] != sha(RULES/'structured_hci_single_revision.py'):
        raise RuntimeError('development used another rule')
    for row in development['outputs']:
        if sha(HERE/'development'/row['report']) != row['report_sha256']:
            raise RuntimeError('development output changed')
    probe = json.loads((HERE/'compiler_probe/results.json').read_text(encoding='utf-8'))
    if sha(HERE/'compiler_probe/source_evidence.json') != probe['source_evidence_sha256']:
        raise RuntimeError('compiler source evidence changed')
    for name, expected in probe['projection_sha256'].items():
        if sha(HERE/'compiler_probe'/name) != expected:
            raise RuntimeError('compiler projection changed')
    if sha(HERE/'compiler_probe/run_probe.py') != probe['runner_sha256']:
        raise RuntimeError('compiler runner changed')
    if sha(HERE/'compiler_probe/scope_tree_original.txt') != probe['scope_dump_sha256']:
        raise RuntimeError('compiler declaration dump changed')
    notes = [HERE/name for name in ('review.md', 'checkpoint.md', 'source_review_raw.json',
             'source_review_cc48.json', 'source_review_fe39.json', 'source_review_fe39.md')]
    report = dict(saved_at_utc=datetime.now(timezone.utc).isoformat(), verified_frozen_files=verified,
                  verified_raw_reports=reports, development_and_compiler_evidence_verified=True,
                  closeout_notes=[dict(path=path.relative_to(RULES).as_posix(), sha256=sha(path)) for path in notes],
                  conclusion='This bounded iteration is saved; D2 generalization and D3 applicability remain open. No new confirmed defect count.')
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print('verified frozen files:', len(verified), 'raw reports:', len(reports))

if __name__ == '__main__':
    main()
