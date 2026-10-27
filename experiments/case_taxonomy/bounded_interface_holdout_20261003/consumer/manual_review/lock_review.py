"""Verify and lock only this new manual-review directory."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent.parent
assert not (HERE / 'lock.json').exists()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


review = load(HERE / 'review.json')
extra = load(HERE / 'source_manifest_extra.json')
assert len(extra) == 8
assert len({(row['revision'], row['source_path']) for row in extra}) == 8
for group in review['quotes'].values():
    for quote in group:
        saved = STAGE / quote['saved_path']
        assert sha(saved) == quote['sha256']
        data = saved.read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest() == quote['blob_sha1']
        lines = saved.read_text(encoding='utf-8').splitlines()
        assert '\n'.join(lines[quote['start_line']-1:quote['end_line']]) == quote['text']
commands = load(HERE / 'commands_extra.json')
for command in commands:
    assert command['returncode'] == 0
    for channel in ('stdout', 'stderr'):
        assert sha(STAGE / command[channel]) == command[channel + '_sha256']
for label in ('parent', 'fixed'):
    raw = STAGE / ('consumer/raw/' + label + '.json')
    assert sha(raw) == review['machine_result'][label + '_raw_sha256']
assert sha(HERE / 'build_review.py') == review['integrity']['review_builder_sha256']
summary = {'status': 'pass', 'source_quotes_verified': sum(len(group) for group in review['quotes'].values()),
           'commands_extra_hashes_verified': len(commands), 'new_sources': 8,
           'sources_per_revision': 4, 'target_emitted': False, 'new_confirmed_cases': 0}
(HERE / 'raw' / 'verify_review.stdout').write_text(json.dumps(summary) + '\n', encoding='utf-8')
entries = [{'path': path.relative_to(HERE).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}
           for path in sorted(HERE.rglob('*')) if path.is_file() and path.name not in ('artifact_manifest.json', 'lock.json')]
(HERE / 'artifact_manifest.json').write_text(json.dumps({'files': entries, 'scope': 'consumer/manual_review only'}, indent=2) + '\n', encoding='utf-8')
lock = {'date': '2026-10-03', 'status': 'locked_pending_root_independent_review',
        'review_json_sha256': sha(HERE / 'review.json'), 'review_md_sha256': sha(HERE / 'review.md'),
        'source_manifest_extra_sha256': sha(HERE / 'source_manifest_extra.json'),
        'artifact_manifest_sha256': sha(HERE / 'artifact_manifest.json'),
        'verification': summary, 'file_count': len(entries),
        'read_only_instruction': 'Do not mutate locked review/source/raw; record later audit at stage root separately.'}
(HERE / 'lock.json').write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8')
print(json.dumps(lock))
