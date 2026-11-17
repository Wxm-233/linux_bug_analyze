"""Reading sheet for the L3 judgement (criteria.md section 3; same as replay_migration_20261105/detect_sheet.py): for every detection answer, the patch's
"修法一致" verdict and reason (test_judgement.json merged with blind_key_test.json), then every issue the model
reported. The judgement itself is written by hand into l3_judgement.json. Windows Python; no model calls.
Output: l3_sheet.md.
"""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-05' / 'migration_checks_20261105'
REPLAY = HERE.parent / 'replay_migration_20261105'


def main():
    judge = json.loads((REPLAY / 'test_judgement.json').read_text(encoding='utf-8'))
    key = json.loads((REPLAY / 'blind_key_test.json').read_text(encoding='utf-8'))
    out = []
    for x in json.loads((HERE / 'l3_index.json').read_text(encoding='utf-8')):
        lab = next(l for l, c in key[x['id']].items() if c == x['cond'])
        verdict = judge[x['id']][lab]
        text = (CALLS / x['dir'] / 'final.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```json\s*(.*?)```', text, re.S)
        try:
            items = json.loads(blocks[-1]) if blocks else None
        except ValueError:
            items = None
        out.append(f'## {x["dir"]}  修法：{verdict[0]}' + (f'（{verdict[1]}：{verdict[2]}）' if len(verdict) > 1 else ''))
        if items is None:
            out.append('（没有解析出JSON）')
        for k, it in enumerate(items or [], 1):
            out.append(f'{k}. [{it.get("机制")}] `{it.get("位置")}`：{it.get("问题")}')
        out.append('')
    (HERE / 'l3_sheet.md').write_text('\n'.join(out), encoding='utf-8')
    print(len(out))


if __name__ == '__main__':
    main()
