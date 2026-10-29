"""Inter-annotator agreement (Claude vs Codex review), adjudication sheet, and coverage under strict/liberal yes (plan.md).
Reads saved labels and per-pair coverage only; no method is rerun. Outputs: agreement.json, adjudication_sheet.csv; prints summary.
"""
from collections import Counter
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parent
C = HERE.parent
CATS = ('yes', 'partial', 'no')


def kappa(a, b, cats):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round(po, 3), (None if pe == 1 else round((po - pe) / (1 - pe), 3))


def main():
    if (HERE / 'agreement.json').exists():
        raise SystemExit('preserve')
    A = {r['id']: r for r in json.loads((C / 'sibling_labels_20261029' / 'labels_103.json').read_text(encoding='utf-8'))['labels']}
    B = {r['id']: r for r in json.loads((C / 'sibling_dataset_20261029' / 'screening_sheet_review.json').read_text(encoding='utf-8'))}
    assert set(A) == set(B) and len(A) == 103
    assert all(B[i]['sibling'] in CATS and B[i]['seed_role'] in ('fix', 'culprit') for i in B)
    sheet = {r['id']: r for r in csv.DictReader(open(C / 'sibling_dataset_20261029' / 'screening_sheet.csv', encoding='utf-8-sig'))}
    cov = {r['id']: r for r in json.loads((C / 'sibling_labels_20261029' / 'analysis.json').read_text(encoding='utf-8'))['rows']}
    ids = sorted(A)
    sa, sb = [A[i]['sibling'] for i in ids], [B[i]['sibling'] for i in ids]
    ra, rb = [A[i]['seed_role'] for i in ids], [B[i]['seed_role'] for i in ids]
    bin_ = lambda xs: ['yes' if x == 'yes' else 'not' for x in xs]
    po3, k3 = kappa(sa, sb, CATS)
    po2, k2 = kappa(bin_(sa), bin_(sb), ('yes', 'not'))
    por, kr = kappa(ra, rb, ('fix', 'culprit'))
    confusion = {'%s|%s' % (x, y): n for (x, y), n in Counter(zip(sa, sb)).items()}
    dis = [i for i in ids if A[i]['sibling'] != B[i]['sibling']]
    kinds = Counter('-'.join(sorted((A[i]['sibling'], B[i]['sibling']))) for i in dis)
    by_type = Counter(sheet[i]['type'] for i in dis)
    with open(HERE / 'adjudication_sheet.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['id', 'type', 'seed', 'seed_subject', 'target', 'target_subject', 'claude_sibling', 'claude_note',
                    'codex_sibling', 'codex_note', 'final_sibling(yes/partial/no)', 'adjudication_note'])
        for i in dis:
            s = sheet[i]
            w.writerow([i, s['type'], s['seed'], s['seed_subject'], s['target'], s['target_subject'], A[i]['sibling'], A[i]['note'],
                        B[i]['sibling'], B[i]['note'], '', ''])
    keys = ('b3_20', 'api_20', 'union_20_20', 'union_all')

    def tally(sel):
        rs = [cov[i] for i in ids if sel(i)]
        return {'pairs': len(rs), **{k: sum(r[k] for r in rs) for k in keys}}
    strict = lambda i: A[i]['sibling'] == 'yes' and B[i]['sibling'] == 'yes'
    liberal = lambda i: A[i]['sibling'] == 'yes' or B[i]['sibling'] == 'yes'
    out = {'pairs': 103,
           'counts': {'claude': dict(Counter(sa)), 'codex': dict(Counter(sb))},
           'sibling_3class': {'agreement': po3, 'kappa': k3},
           'sibling_yes_vs_not': {'agreement': po2, 'kappa': k2},
           'seed_role': {'agreement': por, 'kappa': kr},
           'confusion_claude_by_codex': confusion,
           'disagreements': {'pairs': len(dis), 'kinds': dict(kinds), 'by_type': dict(by_type)},
           'coverage': {'all': tally(lambda i: True), 'claude_yes': tally(lambda i: A[i]['sibling'] == 'yes'),
                        'codex_yes': tally(lambda i: B[i]['sibling'] == 'yes'),
                        'strict_both_yes': tally(strict), 'liberal_either_yes': tally(liberal),
                        'strict_same_dir': tally(lambda i: strict(i) and cov[i]['same_dir_target']),
                        'strict_not_same_dir': tally(lambda i: strict(i) and not cov[i]['same_dir_target']),
                        'neither_yes': tally(lambda i: not liberal(i))}}
    (HERE / 'agreement.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
