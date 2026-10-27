"""Collect only pre-registered parent files. No child message/diff or network."""
from pathlib import Path
import hashlib
import json
import subprocess

stage = Path(__file__).resolve().parent
protocol = json.loads((stage / 'protocol_pre.json').read_text(encoding='utf-8'))
index_path = stage / 'parent_files.json'
if index_path.exists():
    raise SystemExit('Parent collection exists; do not overwrite.')
documents, failures = [], []
for case in protocol['candidates']:
    for relative in case['parent_paths']:
        result = subprocess.run(['git', '-C', '/root/repos/linux', 'show', case['parent'] + ':' + relative], capture_output=True)
        if result.returncode:
            failures.append({'candidate': case['id'], 'revision': case['parent'], 'path': relative, 'error': result.stderr.decode('utf-8', errors='replace')})
            continue
        raw = result.stdout
        target = stage / 'parent_files' / case['id'] / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        documents.append({'id': case['id'] + ':' + relative, 'candidate': case['id'], 'revision': case['parent'], 'path': relative, 'saved_path': str(target.relative_to(stage)), 'bytes': len(raw), 'lines': len(raw.splitlines()), 'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()})
record = {'protocol_sha256': hashlib.sha256((stage / 'protocol_pre.json').read_bytes()).hexdigest(), 'documents': documents, 'failures': failures, 'repair_material_read': False}
index_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'documents': len(documents), 'failures': len(failures), 'candidate_bytes': {c['id']:sum(d['bytes'] for d in documents if d['candidate']==c['id']) for c in protocol['candidates']}}, ensure_ascii=False))
