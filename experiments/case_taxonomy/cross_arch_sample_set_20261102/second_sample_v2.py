"""Second review, round 2 (criteria_amendment3.md): random.Random(20261103) draws 20 C and 20 R rows from
labels_v2.json (not '无关'), excluding the first review's 40, shuffled. Writes second_sample_v2.json (no labels) and
second_sample_v2_key.json.
"""
from pathlib import Path
import json
import random

HERE = Path(__file__).resolve().parent


def main():
    used = {r['id'] for r in json.loads((HERE / 'second_sample.json').read_text(encoding='utf-8'))}
    rows = [r for r in json.loads((HERE / 'labels_v2.json').read_text(encoding='utf-8'))
            if r['flag'] != '无关' and r['id'] not in used]
    rnd = random.Random(20261103)
    pick = rnd.sample([r for r in rows if r['cross'] == 'C'], 20) + rnd.sample([r for r in rows if r['cross'] == 'R'], 20)
    rnd.shuffle(pick)
    blank = [{'id': r['id'], 'commit': r['commit'], 'subject': r['subject']} for r in pick]
    key = [{'id': r['id'], 'mechanism': r['mechanism'], 'cross': r['cross']} for r in pick]
    (HERE / 'second_sample_v2.json').write_text(json.dumps(blank, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'second_sample_v2_key.json').write_text(json.dumps(key, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(pick), sorted(r['id'] for r in pick))


if __name__ == '__main__':
    main()
