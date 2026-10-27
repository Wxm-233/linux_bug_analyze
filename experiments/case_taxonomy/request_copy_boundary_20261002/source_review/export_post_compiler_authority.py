"""Post-harness-read compiler authority; never alters the sealed pre oracle."""
import datetime
import hashlib
import json
import pathlib
import subprocess

STAGE = pathlib.Path(__file__).resolve().parent
REVISIONS = {
    'parent': 'cef456cd354ef485f12d57000c455e83e416a2b6',
    'fixed': '727ea61a5028f8ac96f75ab34cb1b56e63fd9227',
}
files = []
for label, revision in REVISIONS.items():
    raw = subprocess.check_output(['git', '-C', '/root/repos/linux', 'show', revision + ':Makefile'])
    blob = subprocess.check_output(['git', '-C', '/root/repos/linux', 'rev-parse', revision + ':Makefile']).decode().strip()
    target = STAGE / 'post_compiler_authority' / 'raw' / label / 'Makefile'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    hits = [{'line': i, 'text': line} for i, line in enumerate(raw.decode().splitlines(), 1) if '-fno-strict-aliasing' in line]
    files.append({'version': label, 'revision': revision, 'path': 'Makefile',
                  'blob_sha1': blob, 'sha256': hashlib.sha256(raw).hexdigest(),
                  'saved_relative_path': target.relative_to(STAGE).as_posix(), 'relevant_lines': hits})
evidence = {'schema': 'post-harness-compiler-authority-v1',
            'exported_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'read_phase': 'After initial harness/results reading, before final audit binding; supplementary compiler assumption only',
            'pre_harness_oracle_modified': False, 'files': files}
(STAGE / 'post_compiler_authority' / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
print(json.dumps(evidence))
