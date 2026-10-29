"""Apply the user-authorised adjudication rules (rules.md) to the 32 disagreements; write final labels, a spot-check sheet and
coverage on the final yes set. Reads saved labels/coverage only. Outputs: final_labels.json, adjudication_result.csv, final_coverage.json.
"""
from collections import Counter
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parent
C = HERE.parent
RULE1 = ['S013', 'S019', 'S052', 'S054', 'S060', 'S069', 'S076', 'S090', 'S097', 'S098', 'S099', 'S101', 'S102']
RULE2 = ['S%03d' % i for i in range(22, 33)]
CASE = {'S037': 'yes', 'S041': 'yes', 'S047': 'partial', 'S067': 'yes', 'S075': 'yes', 'S091': 'yes', 'S033': 'yes', 'S073': 'partial'}
SPOT = {'S090', 'S102', 'S076'}


def main():
    if (HERE / 'final_labels.json').exists():
        raise SystemExit('preserve')
    A = {r['id']: r for r in json.loads((C / 'sibling_labels_20261029' / 'labels_103.json').read_text(encoding='utf-8'))['labels']}
    B = {r['id']: r for r in json.loads((C / 'sibling_dataset_20261029' / 'screening_sheet_review.json').read_text(encoding='utf-8'))}
    adj = {r['id']: r for r in csv.DictReader(open(C / 'sibling_agreement_20261029' / 'adjudication_sheet.csv', encoding='utf-8-sig'))}
    cov = {r['id']: r for r in json.loads((C / 'sibling_labels_20261029' / 'analysis.json').read_text(encoding='utf-8'))['rows']}
    assert set(adj) == set(RULE1) | set(RULE2) | set(CASE) and len(adj) == 32
    final, basis = {}, {}
    for i in sorted(A):
        if i in RULE1:
            final[i], basis[i] = 'partial', 'rule1'
        elif i in RULE2:
            final[i], basis[i] = 'yes', 'rule2'
        elif i in CASE:
            final[i], basis[i] = CASE[i], 'case'
        else:
            assert A[i]['sibling'] == B[i]['sibling']
            final[i], basis[i] = A[i]['sibling'], 'agreed'
    (HERE / 'final_labels.json').write_text(json.dumps({'adjudicator': 'Claude under user-authorised rules (rules.md)', 'labels':
        [{'id': i, 'sibling': final[i], 'basis': basis[i], 'claude': A[i]['sibling'], 'codex': B[i]['sibling']} for i in sorted(final)]},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    with open(HERE / 'adjudication_result.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['id', 'type', 'seed_subject', 'target_subject', 'claude', 'codex', 'final', 'basis', 'spot_check_suggested'])
        for i in sorted(adj):
            a = adj[i]
            w.writerow([i, a['type'], a['seed_subject'], a['target_subject'], A[i]['sibling'], B[i]['sibling'], final[i], basis[i], int(i in SPOT)])
    keys = ('b3_20', 'api_20', 'union_20_20', 'union_all')

    def tally(sel):
        rs = [cov[i] for i in sorted(final) if sel(i)]
        return {'pairs': len(rs), **{k: sum(r[k] for r in rs) for k in keys}}
    types = sorted({cov[i]['type'] for i in final})
    out = {'final_counts': dict(Counter(final.values())), 'basis_counts': dict(Counter(basis.values())),
           'coverage': {'all': tally(lambda i: True), 'final_yes': tally(lambda i: final[i] == 'yes'),
                        'final_partial': tally(lambda i: final[i] == 'partial'), 'final_no': tally(lambda i: final[i] == 'no'),
                        'final_yes_by_type': {t: tally(lambda i, t=t: final[i] == 'yes' and cov[i]['type'] == t) for t in types},
                        'final_yes_same_dir': tally(lambda i: final[i] == 'yes' and cov[i]['same_dir_target']),
                        'final_yes_not_same_dir': tally(lambda i: final[i] == 'yes' and not cov[i]['same_dir_target']),
                        'strict_both_yes': tally(lambda i: A[i]['sibling'] == 'yes' and B[i]['sibling'] == 'yes'),
                        'liberal_either_yes': tally(lambda i: A[i]['sibling'] == 'yes' or B[i]['sibling'] == 'yes')},
           'final_yes_distinct_targets': len({cov[i]['id'] for i in final if final[i] == 'yes'})}
    (HERE / 'final_coverage.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
