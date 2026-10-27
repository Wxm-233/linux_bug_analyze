"""Check saved source bytes and offered spans without assigning semantics."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
inventory=json.loads((HERE/'inventory.json').read_text(encoding='utf-8'))
materials=json.loads((HERE/'model_materials.json').read_text(encoding='utf-8'))
for version in inventory['versions']:
    for path,meta in version['files'].items():
        raw=(HERE/meta['artifact']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==meta['sha256']
        lines=raw.decode('utf-8').splitlines()
        assert len(lines)==meta['lines']
        for hit in version['hits']:
            if hit['path']==path: assert lines[hit['line']-1]==hit['text']
for doc in materials['documents']:
    p=Path(doc['artifact'])
    if not p.is_absolute(): p=HERE/p
    raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==doc['sha256']
    count=len(raw.decode('utf-8').splitlines())
    for lo,hi in doc['spans']: assert 1<=lo<=hi<=count
prompt=Path(materials['output_directory'])/'prompt.md'
# Windows text writer stores CRLF; runner reads text and sends normalized LF.
assert hashlib.sha256(prompt.read_text(encoding='utf-8').encode()).hexdigest()==materials['prompt_sha256']
plan=json.loads((prompt.parent/'call_plan.json').read_text(encoding='utf-8'))
assert plan['prompt_sha256']==materials['prompt_sha256']
result=dict(status='verified',versioned_files=sum(v['file_count'] for v in inventory['versions']),
            lexical_hit_lines=sum(v['hit_lines'] for v in inventory['versions']),documents=len(materials['documents']),
            prompt_file_sha256=hashlib.sha256(prompt.read_bytes()).hexdigest(),
            prompt_sent_sha256=materials['prompt_sha256'],
            newline_normalization='Windows CRLF file -> runner LF text; both digests retained',
            semantic_approval=False)
supplement=HERE/'supplement_materials.json'
if supplement.exists():
    extra=json.loads(supplement.read_text(encoding='utf-8'))
    for doc in extra['documents']:
        raw=Path(doc['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==doc['sha256']
        count=len(raw.decode('utf-8').splitlines())
        for lo,hi in doc['spans']: assert 1<=lo<=hi<=count
    folder=Path(extra['output_directory'])
    sent=hashlib.sha256((folder/'prompt.md').read_text(encoding='utf-8').encode()).hexdigest()
    assert sent==extra['prompt_sha256']==json.loads((folder/'call_plan.json').read_text(encoding='utf-8'))['prompt_sha256']
    result['supplement']=dict(documents=len(extra['documents']),prompt_sent_sha256=sent,
        prompt_file_sha256=hashlib.sha256((folder/'prompt.md').read_bytes()).hexdigest())
(HERE/'material_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
