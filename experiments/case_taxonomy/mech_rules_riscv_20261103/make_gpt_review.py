"""gpt_review/items.md and answers_template.csv for review_sample.json, without the first annotator's labels and
without the later-fix evidence: each flag with its rule explained and the v6.6 code at the flagged location. WSL."""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
import modules as M  # noqa: E402
RULE = {'R1': '公共代码中的默认实现，arm64、x86、LoongArch三个都提供了自己的版本，只有RISC-V用默认实现。问题是：这个默认实现的假设在RISC-V上是否不成立。',
        'R7': '函数检查过一个可能来自客体或用户的下标的上界，随后用它访问数组，却没有用array_index_nospec，可能存在推测执行越界（Spectre-v1）。',
        'R8': '参照架构的一次修复删掉了某一行写法，而RISC-V同名函数中还保留着完全相同的一行。问题是：参照修掉的问题，RISC-V是否同样存在。',
        'R10': '公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。问题是：RISC-V是否缺少了约定要求的处理。'}


def code(path, s, e):
    lines = M.git('show', f'v6.6:{path}').splitlines()
    e = min(e, s + 70)
    return '\n'.join(f'{k:5d}  {lines[k - 1]}' for k in range(s, min(e, len(lines)) + 1))


rows = json.loads((HERE / 'review_sample.json').read_text(encoding='utf-8'))
md = ['# 待复核的标记（Linux v6.6）\n']
with open(HERE / 'gpt_review/answers_template.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['item', 'label', 'reason'])
    for i, r in enumerate(rows):
        item = f'Q{i:02d}'
        md.append(f'## {item}\n\n**规则**：{RULE[r["rule"]]}\n\n**位置**：`{r["path"]}`中的`{r["name"]}`\n\n'
                  f'**程序给出的理由**：{r["reason"]}\n\n**代码**：\n\n```c\n{code(r["path"], r["start"], r["end"])}\n```\n')
        w.writerow([item, '', ''])
(HERE / 'gpt_review/items.md').write_text('\n'.join(md), encoding='utf-8')
print(len(rows))
