"""Convert labels_103.tsv (id, sibling, seed_role, note) to labels_103.json with annotator metadata."""
from collections import Counter
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
rows = [dict(zip(('id', 'sibling', 'seed_role', 'note'), l.split('\t', 3))) for l in (HERE / 'labels_103.tsv').read_text(encoding='utf-8').splitlines() if l.strip()]
assert len(rows) == 103 and len({r['id'] for r in rows}) == 103
assert all(r['sibling'] in ('yes', 'partial', 'no') and r['seed_role'] in ('fix', 'culprit') for r in rows)
out = {'annotator': 'Claude (claude-opus-5-5), single annotator', 'date': '2026-10-29',
       'standard': 'screening_prep_20261029/标注说明.md and the review guide; B_introducer: yes when T applies to another arch the change S itself made or required',
       'blind_to': 'per-pair method hits and coverage of the new pairs; claude_labels.json not opened during labeling',
       'labels': rows}
(HERE / 'labels_103.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(Counter(r['sibling'] for r in rows), Counter(r['seed_role'] for r in rows))
