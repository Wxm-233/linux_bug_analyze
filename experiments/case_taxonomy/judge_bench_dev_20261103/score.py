"""Scoring (criteria.md section 5). Windows or WSL, no git. Output: scores.json, answers.json,
manual_review_input.json (the flagged positives for the manual consistency check).
"""
from math import comb
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_dev_20261103'
KEY = {'V0': 'verdict', 'V1': 'score'}


def parse(d, key):
    """The last JSON object in final.md that has `key` (nested objects allowed), or None."""
    p = CALLS / d / 'final.md'
    if not p.exists():
        return None
    text = p.read_text(encoding='utf-8', errors='replace')
    dec = json.JSONDecoder()
    for k in range(len(text) - 1, -1, -1):
        if text[k] != '{':
            continue
        try:
            obj, _ = dec.raw_decode(text, k)
        except ValueError:
            continue
        if isinstance(obj, dict) and key in obj:
            return obj
    return None


def lines_of(a):
    out = []
    for x in (a or {}).get('lines') or []:
        if isinstance(x, int) or (isinstance(x, str) and x.strip().isdigit()):
            out.append(int(x))
    return out


def score_of(a):
    try:
        return int(float((a or {}).get('score')))
    except (TypeError, ValueError):
        return None


def flag(var, a, rng):
    if a is None:
        return False
    hit = any(rng[0] <= x <= rng[1] for x in lines_of(a))
    if var == 'V0':
        return str(a.get('verdict')).strip().lower() == 'yes' and hit
    s = score_of(a)
    return s is not None and s >= 2 and hit


def auc(pos, neg):
    if not pos or not neg:
        return None
    w = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(w / (len(pos) * len(neg)), 3)


def mcnemar(b, c):
    n = b + c
    if not n:
        return 1.0
    k = min(b, c)
    return round(min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n), 4)


def main():
    cases = {c['id']: c for c in json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))['cases']}
    index = json.loads((HERE / 'prompt_index.json').read_text(encoding='utf-8'))
    ans = {}
    for it in index:
        a = parse(it['dir'], KEY[it['variant']])
        ans[(it['variant'], it['case'])] = {'dir': it['dir'], 'answered': a is not None,
                                           'flag': flag(it['variant'], a, it['range']), 'answer': a}
    pos = [c for c in cases.values() if c['role'] == 'pos']
    neg = [c for c in cases.values() if c['role'] == 'neg']
    out = {'positives': len(pos), 'positives_built': sum(bool(c['target']) for c in pos), 'negatives': len(neg),
           'positives_with_refs': sum(bool(c['refs']) for c in pos),
           'positives_ref_in_labelled_counterpart_file': sum(
               any(r['path'] in (c['label_counterpart'] or '') for r in c['refs']) for c in pos),
           'variants': {}}
    for var in ('V0', 'V1'):
        g = lambda c: ans.get((var, c['id']), {})
        v = {'pos_flagged': sum(bool(g(c).get('flag')) for c in pos),
             'neg_flagged': sum(bool(g(c).get('flag')) for c in neg),
             'no_answer': sum(1 for c in list(pos) + list(neg) if c['target'] and not g(c).get('answered')),
             'pos_flagged_ids': sorted(c['label_id'] for c in pos if g(c).get('flag')),
             'neg_flagged_ids': sorted(c['id'] for c in neg if g(c).get('flag'))}
        if var == 'V1':
            sp = [score_of(g(c).get('answer')) for c in pos if c['target']]
            sn = [score_of(g(c).get('answer')) for c in neg]
            v['auc_score'] = auc([x if x is not None else -1 for x in sp], [x if x is not None else -1 for x in sn])
            v['score_hist_pos'] = {str(k): sp.count(k) for k in (0, 1, 2, 3, None)}
            v['score_hist_neg'] = {str(k): sn.count(k) for k in (0, 1, 2, 3, None)}
        out['variants'][var] = v
    b = sum(1 for c in pos if ans.get(('V0', c['id']), {}).get('flag') and not ans.get(('V1', c['id']), {}).get('flag'))
    cc = sum(1 for c in pos if not ans.get(('V0', c['id']), {}).get('flag') and ans.get(('V1', c['id']), {}).get('flag'))
    out['mcnemar_pos'] = {'v0_only': b, 'v1_only': cc, 'p': mcnemar(b, cc)}
    v1 = out['variants']['V1']
    out['decision_auto'] = {'pos_ge_11': v1['pos_flagged'] >= 11,
                            'neg_le_10pct': v1['neg_flagged'] <= 5 if len(neg) >= 50
                            else v1['neg_flagged'] <= 0.1 * len(neg),
                            'manual_consistent_ge_8': 'see manual_review.json'}
    (HERE / 'answers.json').write_text(json.dumps(
        [{'variant': k[0], 'case': k[1], **v} for k, v in ans.items()], indent=1, ensure_ascii=False) + '\n',
        encoding='utf-8')
    review = []
    for c in pos:
        for var in ('V0', 'V1'):
            a = ans.get((var, c['id']), {})
            if a.get('flag'):
                review.append({'variant': var, 'id': c['label_id'], 'target': c['target'],
                               'problem': (a['answer'] or {}).get('problem'), 'lines': lines_of(a['answer'])})
    (HERE / 'manual_review_input.json').write_text(json.dumps(review, indent=1, ensure_ascii=False) + '\n',
                                                   encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
