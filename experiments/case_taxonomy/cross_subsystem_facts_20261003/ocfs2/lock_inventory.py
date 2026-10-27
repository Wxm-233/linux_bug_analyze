"""One-shot inventory lock after manual review and integrity verification."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
assert not (HERE / 'lock.json').exists(), 'locked inventories must remain unchanged'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


phase_summaries = {
    'prepare': {'phase': 'prepare', 'resolved_revisions': {
        'parent': '390ac56cf0f687de53695648bc6f2259a7eae429',
        'fix': 'c9dff86eb78a4b6b02b1e407993c946ccaf9bfb4'},
        'sources_saved': 70, 'script_sha256': '71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c'},
    'evidence': {'phase': 'evidence', 'sources_saved_total': 78},
    'replay': {'phase': 'replay', 'tool_and_dependencies_unchanged': True,
               'counts': {'parent': {'candidate': 3, 'normal': 10, 'insufficient': 0},
                          'fix': {'candidate': 0, 'normal': 13, 'insufficient': 0}}},
    'supporting_headers': {'phase': 'supporting_headers', 'sources_saved_total': 86},
}
for phase, summary in phase_summaries.items():
    (HERE / 'raw' / (phase + '_runner.stdout')).write_text(json.dumps(summary) + '\n', encoding='utf-8')
runner_wsl = '/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/cross_subsystem_facts_20261003/ocfs2/runner.py'
python_windows = 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
local_commands = [{'argv': ['wsl', '-d', 'Ubuntu', '--', 'python3', runner_wsl, phase],
                   'tool': 'exec_command', 'sandbox_permissions': 'require_escalated',
                   'prefix_rule': ['wsl', '-d', 'Ubuntu'], 'returncode': 0,
                   'runner_stdout': 'raw/' + phase + '_runner.stdout',
                   'runner_stdout_capture_provenance': 'Exact JSON summary reproduced from tool transcript; all inner process stdout bytes are original files indexed by commands.json',
                   'wsl_transport_warning': 'Tool transcript includes an unrelated localhost/NAT warning with NUL characters; not a SHA and not inner Git/analyzer output'}
                  for phase in phase_summaries]
for script, stdout, note in [('build_facts.py', 'raw/build_facts.stdout', 'Initial assembly before selection snapshot clarification'),
                             ('build_facts.py', 'raw/build_facts_final.stdout', 'Final assembly; initial raw stdout preserved'),
                             ('verify_artifacts.py', 'raw/verify_artifacts.stdout', 'Integrity verification only')]:
    local_commands.append({'argv': [python_windows, '-X', 'utf8',
                           'linux_bug_analyze/experiments/case_taxonomy/cross_subsystem_facts_20261003/ocfs2/' + script],
                           'tool': 'exec_command', 'returncode': 0, 'stdout': stdout, 'note': note})
write('local_commands.json', {'cwd': 'D:/homework/software/linux_bug_analyze',
                              'scope': 'Outer runner/build/verification launch records; inner process byte-exact commands in commands.json',
                              'commands': local_commands})
entries = []
for path in sorted(HERE.rglob('*')):
    if path.is_file() and path.name not in ('artifact_manifest.json', 'lock.json'):
        entries.append({'path': path.relative_to(HERE).as_posix(), 'bytes': path.stat().st_size,
                        'sha256': sha(path)})
write('artifact_manifest.json', {'date': '2026-10-03', 'files': entries,
                                 'excluded_self_and_lock': ['artifact_manifest.json', 'lock.json'],
                                 'locked_scope': 'ocfs2 interface inventory only; no old artifact writes'})
lock = {'date': '2026-10-03', 'state': 'locked_pending_independent_read_only_method_review',
        'artifact_manifest_sha256': sha(HERE / 'artifact_manifest.json'),
        'facts_sha256': sha(HERE / 'facts.json'), 'review_sha256': sha(HERE / 'review.md'),
        'source_manifest_sha256': sha(HERE / 'source_manifest.json'),
        'command_log_sha256': sha(HERE / 'commands.json'),
        'included_file_count': len(entries), 'new_case_count': 0,
        'primary': 'ocfs2_dinode_has_extents.i_flags',
        'method_review_instruction': 'Read only. Keep raw/source/facts/review/manifest/lock immutable; record audit separately at root stage.'}
write('lock.json', lock)
print(json.dumps(lock))
