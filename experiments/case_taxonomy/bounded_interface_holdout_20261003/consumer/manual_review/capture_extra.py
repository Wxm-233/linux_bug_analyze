"""Bounded post-unseal local-source retrieval; no analyzer/build/model execution."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent.parent
LINUX = Path('/root/repos/linux')
REVISIONS = {'parent': 'fac04efc5c793dccbd07e2d59af9f90b7fc0dca4',
             'fixed': '6d44a780635b9b3fb6e20f366ee7750a9adfa884'}
PATHS = ['include/linux/nls.h', 'fs/nls/nls_base.c',
         'fs/smb/client/cifs_unicode.c', 'fs/smb/client/smb2ops.c']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


records = []
commands = []
assert not (HERE / 'source_manifest_extra.json').exists(), 'preserve one-shot evidence'
(HERE / 'raw').mkdir(exist_ok=True)


def run(argv, out):
    process = subprocess.run(argv, cwd=LINUX, capture_output=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(process.stdout)
    err = HERE / 'raw' / (str(len(commands)+1).zfill(3) + '.stderr.bin')
    err.write_bytes(process.stderr)
    commands.append({'argv': argv, 'cwd': str(LINUX), 'returncode': process.returncode,
                     'stdout': out.relative_to(STAGE).as_posix(), 'stdout_sha256': sha(process.stdout),
                     'stderr': err.relative_to(STAGE).as_posix(), 'stderr_sha256': sha(process.stderr)})
    dump('commands_extra.json', commands)
    assert process.returncode == 0, argv
    return process.stdout


for label, revision in REVISIONS.items():
    for path in PATHS:
        out = HERE / 'sources' / label / path
        content = run(['git', 'show', revision + ':' + path], out)
        blob = run(['git', 'rev-parse', revision + ':' + path],
                   HERE / 'raw' / (label + '_' + path.replace('/', '_') + '.blob.stdout.bin')).decode('ascii').strip()
        assert len(blob) == 40 and all(c in '0123456789abcdef' for c in blob)
        records.append({'role': 'consumer_manual_review', 'label': label, 'revision': revision,
                        'source_path': path, 'saved_path': out.relative_to(STAGE).as_posix(),
                        'sha256': sha(content), 'blob_sha1': blob, 'bytes': len(content)})
    run(['git', 'grep', '-n', '-e', 'parse_reparse_point(', '-e', 'cifs_strndup_from_utf16',
         '-e', 'utf8s_to_utf16s', revision, '--', *PATHS],
        HERE / 'raw' / (label + '_direct_edges.stdout.bin'))
dump('source_manifest_extra.json', records)
summary = {'sources_per_revision': 4, 'source_count': 8, 'command_count': len(commands),
           'analyzer_rerun': False, 'compilation': False, 'model_run': False,
           'source_manifest_extra_sha256': sha((HERE / 'source_manifest_extra.json').read_bytes())}
(HERE / 'raw' / 'capture_extra.stdout').write_text(json.dumps(summary) + '\n', encoding='utf-8')
print(json.dumps(summary))
