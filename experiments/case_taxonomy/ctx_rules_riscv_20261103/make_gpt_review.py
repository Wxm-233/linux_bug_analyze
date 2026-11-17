"""gpt_review/items.md and answers_template.csv for all flags of flags_run2.json, without the first annotator's
labels: each flag with its context source explained, the call chain, and the v6.12 code of every function on it."""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402
SRC = {'A:irq': '本函数自己的关中断区间内', 'A:spin': '本函数持有自旋锁的区间内', 'A:raw': '本函数持有raw自旋锁的区间内',
       'A:preempt': '本函数禁抢占的区间内', 'B:trap': '陷入处理函数开头到开中断之前（RISC-V进入陷入处理时中断是关着的）',
       'C:callback': '本函数作为stop_machine或跨核调用的回调执行（中断关闭）',
       'D:hook': '公共代码在原子区间内调用本函数（见“经由”）',
       'N1': '公共代码中标了noinstr/__cpuidle的函数调用了本函数，而参照架构的同名函数标了noinstr/__cpuidle/__always_inline',
       'N2': '本函数标了noinstr，却在instrumentation_begin/end之外调用了可插桩的函数'}
KIND = {'sleep': '可能睡眠', 'rt': '在PREEMPT_RT下会睡眠的普通自旋锁', 'noinstr': '不可插桩约定'}


def code(path, name, start):
    for s, e, n, t in CK.functions('v6.12', path):
        if n == name and (start is None or s == start or s - 8 <= start <= e):
            lines = t.splitlines()[:80]
            return '\n'.join(f'{s + k:5d}  {l}' for k, l in enumerate(lines)) + ('\n...' if e - s >= 80 else '')
    return '（未取到）'


flags = json.loads((HERE / 'flags_run2.json').read_text(encoding='utf-8'))['flags']
md = ['# 待复核的标记（Linux v6.12，RISC-V）\n']
with open(HERE / 'gpt_review/answers_template.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['item', 'label', 'reason'])
    for i, x in enumerate(flags):
        item = f'K{i:02d}'
        chain = '\n'.join(f'- `{c[1]}`（{c[0]}第{c[2]}行调用`{c[3]}`）' for c in x['chain']) or '（直接调用）'
        via = '、'.join(x['via']) if isinstance(x['via'], list) else ''
        parts = [f'## {item}', '',
                 f'**问题种类**：{KIND[x["kind"]]}', '',
                 f'**为什么认为这里不能睡眠/需要不可插桩**：{SRC[x["source"]]}' + (f'；经由：{via}' if via else ''), '',
                 f'**被标记的函数**：`{x["path"]}`中的`{x["function"]}`，第{x["line"]}行调用`{x["call"]}`，最终到达`{x["sink"]}`', '',
                 '**调用链**：', chain, '', '**代码**：', '', f'```c\n{code(x["path"], x["function"], x["start"])}\n```']
        for c in x['chain'][:3]:
            parts += ['', f'`{c[1]}`（{c[0]}）：', '', f'```c\n{code(c[0], c[1], None)}\n```']
        md.append('\n'.join(parts) + '\n')
        w.writerow([item, '', ''])
(HERE / 'gpt_review/items.md').write_text('\n'.join(md), encoding='utf-8')
print(len(flags))
