"""Second-annotator sample (criteria.md section 5): random.Random(20261102) draws 20 C and 20 R rows from the
kept labels (not '无关'), shuffled together. Writes second_sample.json without the researcher's labels (for the second
annotator) and second_sample_key.json with them (for computing agreement afterwards).
"""
from pathlib import Path
import json
import random

HERE = Path(__file__).resolve().parent


def main():
    rows = [r for r in json.loads((HERE / 'labels.json').read_text(encoding='utf-8')) if r['flag'] != '无关']
    rnd = random.Random(20261102)
    pick = rnd.sample([r for r in rows if r['cross'] == 'C'], 20) + rnd.sample([r for r in rows if r['cross'] == 'R'], 20)
    rnd.shuffle(pick)
    blank = [{'id': r['id'], 'commit': r['commit'], 'subject': r['subject'], 'mechanism': '', 'cross': '',
              'counterpart': ''} for r in pick]
    key = [{'id': r['id'], 'mechanism': r['mechanism'], 'cross': r['cross']} for r in pick]
    (HERE / 'second_sample.json').write_text(json.dumps(blank, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'second_sample_key.json').write_text(json.dumps(key, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(pick))


if __name__ == '__main__':
    main()
