"""Fix two metadata leads without reading bodies, patches or source."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
PICKS = [
    ('fe39c7b2dacf', 'net/bluetooth/hci_core.c',
     'Endian-type change lead; whether command-field/copy shape is supported is unknown.'),
    ('cc48dc0a996a', 'net/bluetooth/hci_core.c',
     'Constant cleanup control lead, not presumed a defect; shape and copy entry remain unknown.'),
]

def main():
    poolpath = HERE / 'metadata_pool.json'
    destination = HERE / 'selection_pre.json'
    if destination.exists():
        raise RuntimeError('refusing to overwrite selection')
    rows = json.loads(poolpath.read_text(encoding='utf-8'))['records']
    targets = []
    for prefix, path, role in PICKS:
        matches = [r for r in rows if r['commit'].startswith(prefix)]
        if len(matches) != 1 or path not in matches[0]['paths']:
            raise RuntimeError('target metadata/path not unique')
        row = matches[0]
        parent = subprocess.run(['git', '-C', '/root/repos/linux', 'rev-parse',
                                 row['commit']+'^'], capture_output=True,
                                text=True, check=True).stdout.strip()
        targets.append({**row, 'old_revision':parent, 'source_path':path, 'role':role})
    report = dict(selected_at_utc=datetime.now(timezone.utc).isoformat(), targets=targets,
                  pool_sha256=hashlib.sha256(poolpath.read_bytes()).hexdigest(),
                  reading_audit='Prefix search in experiments/tests/analysis_out excluding metadata pools returned no matching files. This is bounded evidence, not proof of no historical exposure.',
                  reading_scope='Title/date/path and first-parent SHA only; no body, patch or target source read.',
                  limit='Same file at two distinct historical revisions; purpose selection is not an independent population estimate. No replacement after outputs.')
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('fixed targets:', len(targets))

if __name__ == '__main__':
    main()
