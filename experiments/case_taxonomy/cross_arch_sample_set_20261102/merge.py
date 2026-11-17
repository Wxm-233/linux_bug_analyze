"""Merge and freeze the labels (criteria.md sections 5-6). Reads items.json and labels/b*.json, checks every row,
joins the program fields, and writes labels.json plus the report numbers in summary.json. Implementation note
(recorded before any detection method is run): the M2 checker's development fix 83d78ac677b9 (A143, used in
mech_state_size_checker_20261101) is also put in the dev set, which only makes the test set smaller.
"""
from collections import Counter
from pathlib import Path
import glob
import json

HERE = Path(__file__).resolve().parent
MECH = {f'M{i}' for i in range(1, 11)} | {'X1', 'X2'}
FLAGS = {'', '构建错误', '非C代码', '无关'}
EXTRA_DEV = {'83d78ac677b9': 'M2检查器开发用例（mech_state_size_checker_20261101）'}


def check(r):
    i, mech, cx, k, loc, s, mk, fl, why = r
    assert mech in MECH and cx in ('C', 'R') and fl in FLAGS and why, r
    if cx == 'C':
        assert k in ('K1', 'K2', 'K3') and loc and s in ('S0', 'S1', 'S2', 'S3') and mk in tuple('012345'), r
    else:
        assert not (k or loc or s or mk), r


def main():
    items = {i['id']: i for i in json.loads((HERE / 'items.json').read_text(encoding='utf-8'))}
    rows = {}
    for f in sorted(glob.glob(str(HERE / 'labels' / 'b*.json'))):
        for r in json.loads(Path(f).read_text(encoding='utf-8')):
            check(r)
            assert r[0] not in rows, r[0]
            rows[r[0]] = r
    assert set(rows) == set(items), set(rows) ^ set(items)
    out = []
    for i, it in sorted(items.items()):
        _, mech, cx, k, loc, s, mk, fl, why = rows[i]
        dev = it['dev'] or it['commit'] in EXTRA_DEV
        out.append({**it, 'dev': dev, 'dev_extra': EXTRA_DEV.get(it['commit'], ''), 'mechanism': mech, 'cross': cx,
                    'counterpart_kind': k, 'counterpart': loc, 'state': s, 'masking': mk, 'flag': fl, 'reason': why})
    (HERE / 'labels.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8',
                                      newline='\n')
    kept = [r for r in out if r['flag'] != '无关']
    c = [r for r in kept if r['cross'] == 'C']
    c_eval = [r for r in c if r['flag'] != '构建错误']
    test_c = [r for r in c_eval if not r['dev']]
    cnt = lambda rs, key: dict(sorted(Counter(r[key] for r in rs).items()))
    s = {
        'source': {src: {'all': sum(r['source'] == src for r in out),
                         'unrelated': sum(r['source'] == src and r['flag'] == '无关' for r in out),
                         'kept': sum(r['source'] == src for r in kept),
                         'C': sum(r['source'] == src for r in c)} for src in ('A', 'B')},
        'kept': len(kept), 'C': len(c), 'C_share': round(len(c) / len(kept), 3),
        'dev': {'kept': sum(r['dev'] for r in kept), 'C': sum(r['dev'] for r in c)},
        'test': {'kept': sum(not r['dev'] for r in kept), 'C': sum(not r['dev'] for r in c),
                 'C_without_build_errors': len(test_c)},
        'C_without_build_errors': len(c_eval),
        'C_by_mechanism': cnt(c, 'mechanism'), 'C_by_kind': cnt(c, 'counterpart_kind'),
        'C_by_state': cnt(c, 'state'), 'C_by_masking': cnt(c, 'masking'),
        'C_common_triggered': sum(r['common_triggered'] for r in c),
        'build_errors': sum(r['flag'] == '构建错误' for r in kept), 'non_c': sum(r['flag'] == '非C代码' for r in kept),
        'kept_by_mechanism': cnt(kept, 'mechanism'),
        'R_by_mechanism': cnt([r for r in kept if r['cross'] == 'R'], 'mechanism'),
        'dev_label_changes': len(json.loads((HERE / 'labels' / 'dev_changes.json').read_text(encoding='utf-8'))),
    }
    n = len(test_c)
    s['reference_line'] = '够用于评估' if n >= 50 else '有限' if n >= 25 else '不足'
    (HERE / 'summary.json').write_text(json.dumps(s, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(s, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
