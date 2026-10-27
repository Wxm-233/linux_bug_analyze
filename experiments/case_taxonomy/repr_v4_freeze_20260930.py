"""Record the checked implementation before opening fresh target outputs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE = Path(__file__).resolve().parent
FILES = [
    'representation_producer_v4.py',
    'representation_producer_v3.py',
    'endian_consumer_single_revision.py',
    'representation_producer_v4_test.py',
    'repr_v4_run_frozen_20260930.py',
    'repr_v4_patch_select_20260930.py',
    'repr_v3_patch_challenge_strict_select.py',
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out = HERE / 'repr_v4_20260930' / 'freeze_manifest.json'
    if out.exists():
        raise RuntimeError('refusing to replace freeze manifest')
    report = {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'files': [{'path': name, 'sha256': digest(HERE / name)} for name in FILES],
        'protocol_sha256': digest(HERE / 'repr_v4_protocol_20260930_pre.md'),
        'metadata_selection_sha256': digest(HERE / 'repr_v4_selection_20260930_pre.json'),
        'regression': 'Root reran representation_producer_v2/v3/v4 unittest discovery: 44 passed, exit 0. v4 subset: 25 passed.',
        'independent_audit': 'Synthetic/development-only audit: 10 source scenarios and 5 arithmetic boundary scenarios passed; no fresh target source, patch or body read by developers.',
        'scope': 'Only local explicit-endian destination evidence. v4 new macro proof requires source-local definitions visible before write. Header macro, conditional/ambiguous/undefined/shadowed facts are not proof. Candidate is a review lead, not a proven mode/consumer/hardware defect.',
        'zero_sites': 'Out of rule coverage; not a normal outcome.',
    }
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('freeze saved:', report['files'][0]['sha256'])

if __name__ == '__main__':
    main()
