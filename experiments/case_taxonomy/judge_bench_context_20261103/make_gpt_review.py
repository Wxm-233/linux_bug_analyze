import csv, json, subprocess, sys
from pathlib import Path
R = Path(sys.argv[1])
L = {r['id']: r for r in json.load(open(R.parent / 'cross_arch_sample_set_20261102/labels_v2_1.json', encoding='utf-8'))}
def git(*a): return subprocess.run(['git', '-C', '/root/repos/linux', *a], capture_output=True).stdout.decode('utf-8', 'replace')
rows = json.load(open(R / 'manual_review_input.json', encoding='utf-8'))
md = ['# 待复核条目\n']
with open(R / 'gpt_review/answers_template.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['item', 'id', 'label', 'reason'])
    for k, x in enumerate(rows, 1):
        r = L[x['id']]; item = f'H{k:02d}'
        diff = '\n'.join(git('show', '--format=', '-U2', r['commit'], '--', 'arch/riscv').splitlines()[:80])
        md.append(f'## {item}（{x["id"]}）\n\n**被检查的函数**：`{x["target"]["path"]}`中的`{x["target"]["name"]}`\n\n'
                  f'**模型指出的问题**：{x["problem"]}\n\n**真实修复的标题**：{r["subject"]}\n\n**真实修复对RISC-V的改动**：\n\n```diff\n{diff}\n```\n')
        w.writerow([item, x['id'], '', ''])
(R / 'gpt_review/items.md').write_text('\n'.join(md), encoding='utf-8')
print(len(rows))
