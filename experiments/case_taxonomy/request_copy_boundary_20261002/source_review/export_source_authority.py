#!/usr/bin/env python3
"""Export only Git source; never reads experimental harnesses or results."""
import datetime
import hashlib
import json
import pathlib
import subprocess

STAGE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path('/root/repos/linux')
REVISIONS = {
    'parent': 'cef456cd354ef485f12d57000c455e83e416a2b6',
    'fixed': '727ea61a5028f8ac96f75ab34cb1b56e63fd9227',
}
PATHS = [
    'net/bluetooth/hci_core.c',
    'net/bluetooth/hci_request.c',
    'net/bluetooth/hci_request.h',
    'include/net/bluetooth/hci.h',
    'include/net/bluetooth/hci_core.h',
    'include/net/bluetooth/bluetooth.h',
    'include/linux/skbuff.h',
    'include/linux/byteorder/generic.h',
    'include/uapi/linux/byteorder/little_endian.h',
    'include/uapi/linux/byteorder/big_endian.h',
    'arch/x86/include/uapi/asm/byteorder.h',
    'arch/s390/include/uapi/asm/byteorder.h',
    'include/uapi/asm-generic/errno-base.h',
]

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])

manifest = {
    'exported_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'repo': str(REPO),
    'revisions': REVISIONS,
    'read_scope': 'Git source only; harness, runner, results and stdout not read',
    'files': [],
}
for label, revision in REVISIONS.items():
    for source_path in PATHS:
        raw = git('show', f'{revision}:{source_path}')
        blob = git('rev-parse', f'{revision}:{source_path}').decode().strip()
        target = STAGE / 'raw' / label / source_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        manifest['files'].append({
            'version': label,
            'revision': revision,
            'source_path': source_path,
            'blob_sha1': blob,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'byte_count': len(raw),
            'line_count': len(raw.splitlines()),
            'saved_relative_path': target.relative_to(STAGE).as_posix(),
        })
(STAGE / 'source_manifest_pre_harness.json').write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exported_at_utc': manifest['exported_at_utc'], 'files': len(manifest['files'])}))
