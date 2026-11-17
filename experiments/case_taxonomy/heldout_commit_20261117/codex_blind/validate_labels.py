import collections
import hashlib
import json
import pathlib
import re

out = pathlib.Path(__file__).resolve().parent
base = out.parent
criterion_hash = '87c9d3ef0eb376143f6f1af080f8723c249cf50ffb4e7976fd3ef7e1d32b4817'
criteria = (base / 'criteria.md').read_bytes()
assert hashlib.sha256(criteria).hexdigest() == criterion_hash
input_bytes = (base / 'show_heldout.txt').read_bytes()
expected = [(int(k), commit) for k, commit in re.findall(r'^\[(\d+)\] ([0-9a-f]{12}) ', input_bytes.decode('utf-8'), re.M)]
label_bytes = (out / 'codex_label.json').read_bytes()
labels = json.loads(label_bytes)
assert isinstance(labels, list) and len(labels) == len(expected) == 60
assert expected == [(label['k'], label['commit']) for label in labels]
assert [k for k, _ in expected] == list(range(1, 61))
assert len({commit for _, commit in expected}) == 60
required = {'k', 'commit', 'verdict', 'direction', 'category', 'missing', 'archs', 'why'}
categories = {'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'ORD', 'WIDTH', 'OTHER'}
for label in labels:
    assert set(label) == required
    assert type(label['k']) is int
    assert re.fullmatch(r'[0-9a-f]{12}', label['commit'])
    assert label['verdict'] in {'是', '不是', '说不清'}
    assert isinstance(label['why'], str) and label['why'].count('。') >= 2
    if label['verdict'] == '不是':
        assert all(label[field] is None for field in ('direction', 'category', 'missing', 'archs'))
    else:
        assert label['direction'] in {'c2a', 'a2c'}
        assert label['category'] in categories
        assert all(isinstance(label[field], str) and label[field].strip() for field in ('missing', 'archs'))
manifest = json.loads((out / 'patch_manifest.json').read_text(encoding='utf-8'))
assert [(m['k'], m['commit']) for m in manifest] == expected
for item in manifest:
    patch = (out / 'full_patches' / item['file']).read_bytes()
    assert len(patch) == item['bytes']
    assert patch.count(b'\n') == item['lines']
    assert hashlib.sha256(patch).hexdigest() == item['sha256']
    assert patch.startswith(('commit ' + item['commit']).encode('ascii'))
    assert b'\ndiff --git ' in patch
summary = {
    'status': 'pass',
    'items': len(labels),
    'input_order_and_commits_match': True,
    'all_required_fields_and_nulls_valid': True,
    'saved_full_patches_validated': len(manifest),
    'criteria_sha256': criterion_hash,
    'input_sha256': hashlib.sha256(input_bytes).hexdigest(),
    'labels_sha256': hashlib.sha256(label_bytes).hexdigest(),
    'verdict_counts': {key: sum(label['verdict'] == key for label in labels) for key in ('是', '不是', '说不清')},
    'positive_direction_counts': dict(collections.Counter(label['direction'] for label in labels if label['verdict'] == '是')),
    'positive_category_counts': dict(collections.Counter(label['category'] for label in labels if label['verdict'] == '是')),
    'runtime_reproduction_performed': False,
}
(out / 'validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
