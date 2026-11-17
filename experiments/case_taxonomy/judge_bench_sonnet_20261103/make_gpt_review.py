"""Build gpt_review/items.md and answers_template.csv: every positive flagged by DeepSeek or Sonnet, blind to the
first annotator's labels. WSL (git)."""
import csv, json, random, subprocess, sys
from pathlib import Path
R = Path(sys.argv[1]); DEV = R.parent / 'judge_bench_dev_20261103'
L = {r['id']: r for r in json.load(open(R.parent / 'cross_arch_sample_set_20261102/labels_v2_1.json', encoding='utf-8'))}
def git(*a): return subprocess.run(['git', '-C', '/root/repos/linux', *a], capture_output=True).stdout.decode('utf-8', 'replace')
rows = []
for model, d in (('DeepSeek-V4.1-Flash', DEV), ('Claude-Sonnet-5.5', R)):
    for x in json.load(open(d / 'manual_review_input.json', encoding='utf-8')):
        rows.append((model, x))
random.Random(20261107).shuffle(rows)
md = ['# 待复核条目（顺序已打乱）\n']
with open(R / 'gpt_review/answers_template.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['item', 'id', 'label', 'reason'])
    for k, (model, x) in enumerate(rows, 1):
        r = L[x['id']]; item = f'G{k:02d}'
        diff = '\n'.join(git('show', '--format=', '-U2', r['commit'], '--', 'arch/riscv').splitlines()[:80])
        md.append(f'## {item}（{x["id"]}）\n\n**被检查的函数**：`{x["target"]["path"]}`中的`{x["target"]["name"]}`\n\n'
                  f'**模型指出的问题**：{x["problem"]}\n\n**真实修复的标题**：{r["subject"]}\n\n**真实修复对RISC-V的改动**：\n\n```diff\n{diff}\n```\n')
        w.writerow([item, x['id'], '', ''])
(R / 'gpt_review/items.md').write_text('\n'.join(md), encoding='utf-8')
json.dump([{'item': f'G{k:02d}', 'model': m, 'variant': x['variant'], 'id': x['id']} for k, (m, x) in enumerate(rows, 1)],
          open(R / 'gpt_review_key.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(rows))
