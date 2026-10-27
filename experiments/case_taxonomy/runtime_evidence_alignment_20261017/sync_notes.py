"""Synchronize only the two explicitly maintained current research notes."""
from pathlib import Path
import hashlib
import json

STAGE = Path('/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/runtime_evidence_alignment_20261017')
WINDOWS = Path('/mnt/d/homework/software/linux_bug_analyze')
EXPECTED = {
    '当前代办.md': 'eed0527d37c8d6ff2da5917e55bcefe0cac574359906df6ef4f3e60620e29a5a',
    '当前研究方向与进展.md': '74b51c9f099a654db4eaee401b07a9829fb8461c02ab4037571dd2bb0834a0ed',
}
def sha(data):
    return hashlib.sha256(data).hexdigest()

rows = []
for name, expected in EXPECTED.items():
    target = Path('/root') / name
    payload = (WINDOWS / name).read_bytes()
    prior = sha(target.read_bytes())
    if prior != expected:
        raise RuntimeError('WSL note changed independently: ' + name)
    rows.append((target, payload, {'name': name, 'before_sha256': prior,
                                  'after_sha256': sha(payload)}))
for target, payload, row in rows:
    target.write_bytes(payload)
    if target.read_bytes() != payload:
        raise RuntimeError('sync mismatch: ' + target.name)
    row['windows_wsl_equal'] = True
receipt = STAGE / 'notes_sync.json'
if receipt.exists():
    raise RuntimeError('receipt exists')
receipt.write_text(json.dumps({'status': 'PASS', 'files': [r for _, _, r in rows]},
                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'synchronized_notes': len(rows)}))
