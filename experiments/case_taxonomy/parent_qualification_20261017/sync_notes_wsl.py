from pathlib import Path
import hashlib
import json

stage=Path('/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/parent_qualification_20261017')
outer=Path('/mnt/d/homework/software/linux_bug_analyze')
records=json.loads((stage/'notes_sync.json').read_text(encoding='utf-8'))
for name,item in records.items():
    target=Path('/root')/name
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() not in {item['before_sha256'],item['after_sha256']}:
        raise RuntimeError('WSL note independently changed: '+name)
for name,item in records.items():
    target=Path('/root')/name
    target.write_bytes((outer/name).read_bytes())
    assert hashlib.sha256(target.read_bytes()).hexdigest()==item['after_sha256']
print(json.dumps({'status':'synchronized_byte_equal','files':list(records)},ensure_ascii=False))
