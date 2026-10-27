"""Synchronize only the two explicitly registered current-checkpoint notes."""
from pathlib import Path
import hashlib
import json

stage=Path(__file__).resolve().parent
outer=stage.parents[2].parent
receipt=json.loads((stage/'notes_sync.json').read_text(encoding='utf-8'))
allowed={'当前代办.md','当前研究方向与进展.md'}
assert set(receipt)==allowed
for name,record in receipt.items():
    original=outer/name
    target=Path('/root')/name
    assert hashlib.sha256(original.read_bytes()).hexdigest()==record['after_sha256']
    if target.exists():
        assert hashlib.sha256(target.read_bytes()).hexdigest() in {record['before_sha256'],record['after_sha256']}, 'Independent WSL change: '+name
for name,record in receipt.items():
    target=Path('/root')/name
    target.write_bytes((outer/name).read_bytes())
    assert hashlib.sha256(target.read_bytes()).hexdigest()==record['after_sha256']
print(json.dumps({'status':'Windows_WSL_notes_byte_equal','files':sorted(allowed)},ensure_ascii=False))
