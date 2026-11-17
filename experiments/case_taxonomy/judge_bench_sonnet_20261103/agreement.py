"""Agreement between the first annotator (manual_review.json of both rounds) and GPT (gpt_review/answers.csv) on
the 28 flagged positives, and the consistent counts per model and question style under each annotator. No git."""
from collections import Counter
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parent
DEV = HERE.parent / 'judge_bench_dev_20261103'
MODELS = {'DeepSeek-V4.1-Flash': DEV, 'Claude-Sonnet-5.5': HERE}


def main():
    key = {k['item']: k for k in json.loads((HERE / 'gpt_review_key.json').read_text(encoding='utf-8'))}
    gpt = {r['item']: r for r in csv.DictReader(open(HERE / 'gpt_review' / 'answers.csv', encoding='utf-8-sig'))}
    mine = {}
    for m, d in MODELS.items():
        for r in json.loads((d / 'manual_review.json').read_text(encoding='utf-8'))['rows']:
            mine[(m, r['variant'], r['id'])] = r['label']
    rows = []
    for item, k in sorted(key.items()):
        assert gpt[item]['id'] == k['id']
        rows.append({'item': item, 'model': k['model'], 'variant': k['variant'], 'id': k['id'],
                     'first': mine[(k['model'], k['variant'], k['id'])], 'gpt': gpt[item]['label']})
    n = len(rows)
    po = sum(r['first'] == r['gpt'] for r in rows) / n
    a, b = Counter(r['first'] for r in rows), Counter(r['gpt'] for r in rows)
    pe = sum(a[x] * b[x] for x in set(a) | set(b)) / n / n
    counts = {}
    for m in MODELS:
        for v in ('V0', 'V1'):
            rs = [r for r in rows if r['model'] == m and r['variant'] == v]
            counts[f'{m} {v}'] = {who: dict(Counter(r[who] for r in rs)) for who in ('first', 'gpt')}
    out = {'items': n, 'agreement': round(po, 3), 'kappa': round((po - pe) / (1 - pe), 3) if pe < 1 else None,
           'disagreements': [r for r in rows if r['first'] != r['gpt']], 'counts': counts}
    (HERE / 'agreement.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
