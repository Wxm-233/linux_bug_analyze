"""gpt_review/items.md and answers_template.csv: one item per issue of flags_end.json with the end-version code of
the flagged function and of the chain functions, without the first annotator's labels. WSL."""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402
REV = 'df2908090cda'
WHY = {'A': '本函数自己的原子区间内（关中断、持锁或禁抢占）', 'B': '陷入处理函数开中断之前（RISC-V进入陷入处理时中断关闭）',
       'C': '作为stop_machine或跨核调用回调执行', 'D': '公共代码在原子区间内调用本函数',
       'N': '不可插桩（noinstr）约定'}
RULE = {'CTX': '执行上下文：在不能睡眠或不能插桩的地方，做了可能睡眠或会被插桩的事。',
        'R7': '推测执行越界（Spectre-v1）：检查过上界的、可能来自客体或用户的下标，没有用array_index_nospec就访问数组。',
        'R10': '同一约定：arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。'}


def code(path, name, limit=70):
    for s, e, n, t in CK.functions(REV, path):
        if n == name:
            lines = t.splitlines()[:limit]
            return '\n'.join(f'{s + k:5d}  {l}' for k, l in enumerate(lines)) + ('\n...' if e - s >= limit else '')
    return '（未取到）'


flags = json.loads((HERE / 'flags_end.json').read_text(encoding='utf-8'))['flags']
issues = {}
for f in flags:
    issues.setdefault(f['issue'], []).append(f)
md = ['# 待复核的问题（Linux终点版本df2908090cda，RISC-V）\n']
with open(HERE / 'gpt_review/answers_template.csv', 'w', encoding='utf-8', newline='') as w:
    cw = csv.writer(w); cw.writerow(['item', 'label', 'reason'])
    for k, fs in enumerate(issues.values()):
        f = fs[0]
        src = WHY.get((f.get('source') or 'N')[0], '') if f['rule'] == 'CTX' else ''
        parts = [f'## E{k:02d}', '', f'**规则**：{RULE[f["rule"]]}', '']
        if src:
            parts += [f'**原子上下文的来源**：{src}', '']
        parts += ['**被标记的位置**：' + '；'.join(f'`{g["path"]}`中的`{g["name"]}`（{g["reason"][:160]}）' for g in fs[:3]), '',
                  '**调用链**：' + (' → '.join(f'`{c[1]}`调用`{c[3]}`' for c in f.get('chain') or []) or '（直接）'), '',
                  '```c', code(f['path'], f['name']), '```']
        for c in (f.get('chain') or [])[:2]:
            parts += ['', f'`{c[1]}`（{c[0]}）：', '```c', code(c[0], c[1], 50), '```']
        md.append('\n'.join(parts) + '\n')
        cw.writerow([f'E{k:02d}', '', ''])
(HERE / 'gpt_review/items.md').write_text('\n'.join(md), encoding='utf-8')
print(len(issues))
