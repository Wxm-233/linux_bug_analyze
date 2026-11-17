"""Tuning view (criteria.md section 4): the flags of a run with every flag that hits an evaluation positive hidden,
counted per rule, and a few shown per rule. WSL. Usage: python3 tune_view.py FLAGS.json [PER_RULE]"""
from pathlib import Path
import json
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score as S  # noqa: E402


def main():
    flags = json.loads((HERE / sys.argv[1]).read_text(encoding='utf-8'))['flags']
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    labels = json.loads(S.LABELS.read_text(encoding='utf-8'))
    ev = [r for r in labels if r['cross'] == 'C' and r['flag'] not in ('无关', '构建错误')
          and S.SNAP_DATE <= r['date'] <= S.WIN_END and not r['dev']]
    keep = [f for f in flags if not any(S.hit(f, r) for r in ev)]
    print('hidden', len(flags) - len(keep), 'shown', len(keep))
    for rule in S.MECH:
        fs = [f for f in keep if f['rule'] == rule]
        print(f'== {rule}: {len(fs)}')
        for f in random.Random(1).sample(fs, min(per, len(fs))):
            print(f'  {f["path"]}:{f["name"]} | {f["reason"][:230]}')


if __name__ == '__main__':
    main()
