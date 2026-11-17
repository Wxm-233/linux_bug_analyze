"""Agreement between the first-pass labels and the second annotator (criteria_amendment.md): percent agreement and
Cohen's kappa for C/R and for the mechanism, and the list of disagreements. Reads second_review/answers.csv and
second_sample_key.json; does not change labels.json. Output: agreement.json. Arguments: key file, answer folder,
output file (default second_sample_key.json second_review agreement.json).
"""
from collections import Counter
from pathlib import Path
import csv
import json
import sys

HERE = Path(__file__).resolve().parent
ARGS = sys.argv[1:] or ['second_sample_key.json', 'second_review', 'agreement.json']
MECH = {f'M{i}' for i in range(1, 11)} | {'X1', 'X2'}


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0, round(po, 3)


def main():
    key = {r['id']: r for r in json.loads((HERE / ARGS[0]).read_text(encoding='utf-8'))}
    with open(HERE / ARGS[1] / 'answers.csv', encoding='utf-8-sig', newline='') as f:
        ans = {r['编号'].strip(): r for r in csv.DictReader(f)}
    assert set(ans) == set(key), set(ans) ^ set(key)
    ids = sorted(key)
    bad = [i for i in ids if ans[i]['机制'].strip() not in MECH or ans[i]['跨架构'].strip() not in ('C', 'R')]
    assert not bad, bad
    first_cx = [key[i]['cross'] for i in ids]
    second_cx = [ans[i]['跨架构'].strip() for i in ids]
    first_m = [key[i]['mechanism'] for i in ids]
    second_m = [ans[i]['机制'].strip() for i in ids]
    k_cx, p_cx = kappa(first_cx, second_cx)
    k_m, p_m = kappa(first_m, second_m)
    diff = [{'id': i, 'first': [key[i]['mechanism'], key[i]['cross']],
             'second': [ans[i]['机制'].strip(), ans[i]['跨架构'].strip()],
             'second_counterpart': ans[i]['对应物位置'].strip(), 'second_reason': ans[i]['理由'].strip()}
            for i in ids if (key[i]['mechanism'], key[i]['cross']) != (ans[i]['机制'].strip(), ans[i]['跨架构'].strip())]
    out = {'n': len(ids),
           'cross': {'agreement': p_cx, 'kappa': k_cx,
                     'table': dict(Counter(f'{a}/{b}' for a, b in zip(first_cx, second_cx)))},
           'mechanism': {'agreement': p_m, 'kappa': k_m},
           'reference_line': '一致性较好' if k_cx >= 0.6 else '中等' if k_cx >= 0.4 else '较差',
           'disagreements': diff}
    (HERE / ARGS[2]).write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'disagreements'}, indent=1, ensure_ascii=False))
    print('disagreements:', len(diff))


if __name__ == '__main__':
    main()
