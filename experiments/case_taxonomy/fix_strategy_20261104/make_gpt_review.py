"""GPT review material (criteria.md section 5): 30 of the 135 items, stratified by mechanism (proportional, at least
one per mechanism, seed 20261105), each with the fix commit's message and diff from dump/ and the definitions of
criteria_amendment1.md, without the first annotator's labels. The key is written separately. No git, no model.
Output: gpt_review/review_items.md, gpt_review_key.json (kept outside gpt_review/ so the folder can be handed over whole)."""
from pathlib import Path
import json
import random
import re

HERE = Path(__file__).resolve().parent
N, SEED = 30, 20261105


def blocks():
    out = {}
    for p in sorted((HERE / 'dump').glob('*.txt')):
        for b in re.split(r'\n(?=##### )', p.read_text(encoding='utf-8')):
            m = re.match(r'##### (\S+) ', b)
            if m:
                lines = [l for l in b.strip().splitlines() if not l.startswith('样本集标签：')]
                out[m.group(1)] = '\n'.join(lines)
    return out


def main():
    rows = json.loads((HERE / 'fix_labels.json').read_text(encoding='utf-8'))
    rng = random.Random(SEED)
    by = {}
    for r in rows:
        by.setdefault(r['mechanism'], []).append(r)
    quota = {m: max(1, round(N * len(v) / len(rows))) for m, v in by.items()}
    while sum(quota.values()) > N:
        quota[max(quota, key=lambda m: quota[m])] -= 1
    while sum(quota.values()) < N:
        quota[max(by, key=lambda m: len(by[m]) - quota[m])] += 1
    picked = sorted((r for m, v in by.items() for r in rng.sample(v, quota[m])), key=lambda r: r['id'])
    text = (HERE / 'criteria_amendment1.md').read_text(encoding='utf-8')
    defs = text[text.index('## 定稿的修复动作'):]
    crit = (HERE / 'criteria.md').read_text(encoding='utf-8')
    fields = crit[crit.index('## 二、标注字段'):crit.index('## 三、')]
    b = blocks()
    parts = ['# 修复方式标注复核材料', '',
             '下面30条都是Linux内核中的跨架构缺陷修复提交（缺陷只在RISC-V或部分架构上出现）。请对每条独立判断以下字段，'
             '不要参考任何已有标注。每条给出“对应物”，即其他架构或公共代码中处理同一条件的代码位置。', '',
             fields.strip(), '', defs.strip(), '',
             '请按如下格式逐条回答：`编号 | action（主动作在前） | follow | layer | cites | 一句话理由`', '']
    for k, r in enumerate(picked, 1):
        parts += [f'## {k}. {r["id"]}', f'对应物：{r["counterpart"]}', '', '```', b[r['id']], '```', '']
    (HERE / 'gpt_review' / 'review_items.md').write_text('\n'.join(parts) + '\n', encoding='utf-8')
    key = [{k: r[k] for k in ('id', 'mechanism', 'state', 'action', 'follow', 'layer', 'cites', 'note')} for r in picked]
    (HERE / 'gpt_review_key.json').write_text(json.dumps(key, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(picked), quota)


if __name__ == '__main__':
    main()
