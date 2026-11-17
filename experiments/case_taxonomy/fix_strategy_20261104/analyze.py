"""Merge the first-annotator fix labels (labels_dev.py, labels_test.py) with the sample-set fields of items.json and
compute the tables of criteria.md section 4. No git, no model. Output: fix_labels.json, tables.json."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from labels_dev import L as DEV  # noqa: E402
from labels_test import L as TEST  # noqa: E402

ACT = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A0']
FOL = ['F1', 'F2', 'F3', 'F4']
MECH = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10']


def table(rows, key):
    out = {}
    for m in MECH:
        rs = [r for r in rows if r['mechanism'] == m]
        if rs:
            out[m] = {'n': len(rs), **{k: v for k, v in Counter(key(r) for r in rs).most_common()}}
    return out


def main():
    items = json.loads((HERE / 'items.json').read_text(encoding='utf-8'))
    assert not set(DEV) & set(TEST)
    lab = {**DEV, **TEST}
    ids = {r['id'] for r in items}
    assert set(lab) == ids, (sorted(ids - set(lab)), sorted(set(lab) - ids))
    for r in items:
        assert (r['id'] in DEV) == r['dev'], r['id']
        a, f, layer, cites, note = lab[r['id']]
        assert all(x in ACT for x in a) and f in FOL and layer in ('A', 'C', 'AC') and cites in 'YN'
        r.update(action=a, main=a[0], follow=f, layer=layer, cites=cites, note=note)
    (HERE / 'fix_labels.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    out = {}
    for name, rows in (('all', items), ('dev', [r for r in items if r['dev']]), ('test', [r for r in items if not r['dev']])):
        out[name] = {
            'n': len(rows),
            'main_action': dict(Counter(r['main'] for r in rows).most_common()),
            'follow': dict(Counter(r['follow'] for r in rows).most_common()),
            'layer': dict(Counter(r['layer'] for r in rows).most_common()),
            'cites': dict(Counter(r['cites'] for r in rows)),
            'mech_x_action': table(rows, lambda r: r['main']),
            'mech_x_follow': table(rows, lambda r: r['follow']),
            'state_x_follow': {s: dict(Counter(r['follow'] for r in rows if r['state'] == s)) for s in ('S1', 'S2', 'S3', 'S0')},
            'cites_x_follow': {c: dict(Counter(r['follow'] for r in rows if r['cites'] == c)) for c in 'YN'},
            'source_x_layer': {s: dict(Counter(r['layer'] for r in rows if r['source'] == s)) for s in 'AB'},
        }
    (HERE / 'tables.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    a = out['all']
    for k in ('n', 'main_action', 'follow', 'layer', 'cites', 'state_x_follow', 'cites_x_follow', 'source_x_layer'):
        print(k, a[k])
    print('mech x action'); [print(' ', m, v) for m, v in a['mech_x_action'].items()]
    print('mech x follow'); [print(' ', m, v) for m, v in a['mech_x_follow'].items()]
    print('dev follow', out['dev']['follow'], 'test follow', out['test']['follow'])
    print('dev main', out['dev']['main_action'], '\ntest main', out['test']['main_action'])
    for r in items:
        if r['follow'] in ('F2', 'F3'):
            print(r['id'], r['mechanism'], r['follow'], r['note'][:70])


if __name__ == '__main__':
    main()
