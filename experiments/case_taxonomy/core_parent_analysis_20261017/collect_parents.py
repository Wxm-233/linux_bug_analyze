"""Exact-parent collection for the two registered source qualifications."""
from pathlib import Path
import hashlib
import json
import subprocess

stage = Path(__file__).resolve().parent
p = json.loads((stage / 'protocol_pre.json').read_text(encoding='utf-8'))
out = stage / 'parent_files.json'
if out.exists():
    raise SystemExit('Already collected; preserve original.')
documents = []
for case in p['cases']:
    for path in case['initial_paths']:
        proc = subprocess.run(['git', '-C', p['collection']['git'], 'show', case['parent'] + ':' + path], capture_output=True, timeout=30)
        record = {'id': case['id'] + ':' + path, 'case': case['id'], 'parent': case['parent'], 'path': path}
        if proc.returncode:
            record.update(status='unavailable', error=proc.stderr.decode('utf-8', errors='replace')[:1000])
        else:
            target = stage / 'parent_sources' / case['id'] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(proc.stdout)
            record.update(status='collected', saved_path=str(target.relative_to(stage)), bytes=len(proc.stdout), sha256=hashlib.sha256(proc.stdout).hexdigest(), lines=len(proc.stdout.splitlines()))
        documents.append(record)
out.write_text(json.dumps({'protocol_sha256': hashlib.sha256((stage/'protocol_pre.json').read_bytes()).hexdigest(), 'documents': documents, 'child_message_or_patch_read': False}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'documents':len(documents), 'collected':sum(d['status']=='collected' for d in documents),'bytes_by_case':{c['id']:sum(d.get('bytes',0) for d in documents if d['case']==c['id']) for c in p['cases']}},ensure_ascii=False))
