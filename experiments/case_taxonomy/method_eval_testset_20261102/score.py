"""Score results.json against labels_v2_1.json (criteria.md section 3). Output: scores.json."""
from collections import Counter
from datetime import date
from math import comb
from pathlib import Path
import json
import statistics

HERE = Path(__file__).resolve().parent
LABELS = HERE.parent / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
METHODS = {'F1': lambda r: bool(r['F1']), 'F2': lambda r: bool(r['F2']), 'R2': lambda r: bool(r['R2']),
           'R5': lambda r: bool(r['R5'])}
METHODS['F1∪F2'] = lambda r: bool(r['F1'] or r['F2'])
METHODS['全部'] = lambda r: any(f(r) for k, f in list(METHODS.items()) if k in ('F1', 'F2', 'R2', 'R5'))


def fisher(a, b, c, d):
    """Two-sided Fisher exact test on [[a, b], [c, d]]."""
    n, r1, c1 = a + b + c + d, a + b, a + c
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    obs = p(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return round(min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9))), 4)


def frac(k, n):
    return [k, n, round(k / n, 3) if n else None]


def main():
    labels = {r['id']: r for r in json.loads(LABELS.read_text(encoding='utf-8'))}
    res = json.loads((HERE / 'results.json').read_text(encoding='utf-8'))
    errors = [r['id'] for r in res if 'error' in r]
    res = [r for r in res if 'error' not in r]
    pos = [r for r in res if labels[r['id']]['cross'] == 'C' and labels[r['id']]['flag'] != '构建错误']
    neg = [r for r in res if labels[r['id']]['cross'] == 'R' and labels[r['id']]['flag'] != '构建错误']
    pa, na = [r for r in pos if r['applicable']], [r for r in neg if r['applicable']]
    out = {'errors': errors, 'positives': len(pos), 'positives_applicable': len(pa), 'controls': len(neg),
           'controls_applicable': len(na), 'methods': {}}
    for m, f in METHODS.items():
        hp, hn = sum(f(r) for r in pa), sum(f(r) for r in na)
        row = {'positives_all': frac(sum(f(r) for r in pos), len(pos)), 'positives_applicable': frac(hp, len(pa)),
               'controls_all': frac(sum(f(r) for r in neg), len(neg)), 'controls_applicable': frac(hn, len(na)),
               'fisher_p_applicable': fisher(hp, len(pa) - hp, hn, len(na) - hn)}
        rp, rn = hp / len(pa) if pa else 0, hn / len(na) if na else 0
        row['discriminates'] = bool(rp >= 2 * rn and rp > 0 and row['fisher_p_applicable'] < 0.05)
        hits = [r for r in pos if f(r)]
        row['hit_ids'] = [r['id'] for r in hits]
        for key in ('mechanism', 'masking', 'counterpart_kind'):
            row[f'hits_by_{key}'] = dict(sorted(Counter(labels[r['id']][key] for r in hits).items()))
        if m in ('F1', 'F2'):
            lead = [(date.fromisoformat(r['date']) - min(date.fromisoformat(x['ref_date']) for x in r[m])).days
                    for r in hits]
            row['lead_days'] = {'median': statistics.median(lead), 'min': min(lead), 'max': max(lead)} if lead else None
            row['control_hit_ids'] = [r['id'] for r in neg if f(r)]
        out['methods'][m] = row
    allf = METHODS['全部']
    out['positives_missed'] = {'not_applicable': sum(not r['applicable'] for r in pos),
                               'applicable_not_flagged': sum(r['applicable'] and not allf(r) for r in pos)}
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
