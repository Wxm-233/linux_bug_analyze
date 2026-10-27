"""Integrity assertions for the locked inventory, not new detector tests."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAXONOMY = HERE.parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


source_manifest = load('source_manifest.json')
commands = load('commands.json')
facts = load('facts.json')
assert len(source_manifest) == len({(item['revision'], item['path']) for item in source_manifest}) == 86
for entry in source_manifest:
    path = HERE / entry['saved_path']
    data = path.read_bytes()
    assert sha(path) == entry['sha256']
    git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
    assert git_blob == entry['blob'], entry['path']
for command in commands:
    assert command['returncode'] == 0
    for channel in ('stdout', 'stderr'):
        assert sha(HERE / command[channel]) == command[channel + '_sha256']
for entry in facts['reviewed_facts']['entries']:
    for evidence in entry.get('evidence', []):
        path = HERE / evidence['saved_path']
        assert sha(path) == evidence['sha256']
        lines = path.read_text(encoding='utf-8').splitlines()
        excerpt = '\n'.join(lines[evidence['line_start']-1:evidence['line_end']])
        assert excerpt == evidence['excerpt'], entry['id']
for label in ('parent', 'fix'):
    raw = load('raw/' + label + '.json')
    original = json.loads((TAXONOMY / ('endian_consumer_ocfs2_' + label + '.json')).read_text(encoding='utf-8'))
    assert raw == original, 'known development replay differs from original output'
    summary = facts['automatic_facts']['revisions'][label]
    assert sha(HERE / summary['raw_output']) == summary['raw_sha256']
    assert raw['revision'] == summary['revision']
    assert summary['primary'] in raw['findings']
    assert all(row in raw['findings'] for row in summary['normal_control_reads'])
    saved = {row['path']: row for row in source_manifest if row['revision'] == raw['revision']}
    assert all(saved[row['path']]['sha256'] == row['sha256'] for row in raw['files_read'])
state_before = load('tool_before_replay.json')
assert state_before == load('tool_after_replay.json') == load('final_tool_state.json')
assert sha(TAXONOMY / 'endian_consumer_single_revision.py') == state_before['script_sha256']
assert sha(HERE.parent / 'protocol_pre.md') == state_before['protocol_sha256']
assert facts['selection']['phase_at_selection'] == load('prepared.json')['phase']
assert 'phase' not in facts['selection']
summary = {'status': 'pass', 'sources_sha256_and_git_blob_verified': 86,
           'captured_commands_and_raw_hashes_verified': len(commands),
           'known_replay_equals_existing_outputs': True,
           'reviewed_excerpt_bindings_verified': sum(len(row.get('evidence', [])) for row in facts['reviewed_facts']['entries']),
           'original_script_and_protocol_unchanged': True,
           'no_kernel_execution_or_compilation': True}
(HERE / 'raw' / 'verify_artifacts.stdout').write_text(json.dumps(summary) + '\n', encoding='utf-8')
print(json.dumps(summary))
