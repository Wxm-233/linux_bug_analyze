"""Blind GPT review material (criteria.md section 2): all 60 LoongArch items, each as its control prompt C0_nn (the
plain prompt, no labels, no claims), with instructions and an answer template. No git, no model.
Output: gpt_review/复核说明.md, items.md, answers_template.csv."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_expand_20261103'
GUIDE = '''# 复核说明：程序规则标出的问题是不是真问题

`items.md`中共{n}条。每条都是一个程序规则在某个Linux内核版本的**LoongArch**代码中标出的问题，附有规则说明、位置、理由、调用链和当时的代码。

请判断每条在**它所写的那个内核版本中**是不是真问题，选一个标签：

| 标签 | 含义 |
| --- | --- |
| `real` | 真问题：确实会导致错误行为、警告误报、安全问题，或违反内核约定 |
| `false_alarm` | 不是问题：例如路径走不到、锁已释放、下标不受不可信方控制、该版本不能开启相关配置、只是缺少某项功能或优化 |
| `unsure` | 判断不了 |

可以使用你对内核的了解，包括查看上游后来的提交。理由写一句话。

填写`answers_template.csv`，另存为`answers.csv`：保留表头和第一列，不改变行的顺序。
'''


def main():
    out = HERE / 'gpt_review'
    if out.exists():
        raise SystemExit('preserve')
    out.mkdir()
    ctrl = json.loads((HERE / 'control_index.json').read_text(encoding='utf-8'))
    parts = [f'# 待复核的标记（{len(ctrl)}条）', '']
    for c in ctrl:
        parts += [f'## {c["dir"]}', '', (CALLS / c['dir'] / 'prompt.md').read_text(encoding='utf-8').rstrip(), '']
    (out / 'items.md').write_text('\n'.join(parts) + '\n', encoding='utf-8', newline='\n')
    (out / '复核说明.md').write_text(GUIDE.format(n=len(ctrl)), encoding='utf-8', newline='\n')
    (out / 'answers_template.csv').write_text('item,label,reason\n' + ''.join(f'{c["dir"]},,\n' for c in ctrl),
                                             encoding='utf-8', newline='\n')
    print(len(ctrl), 'items')


if __name__ == '__main__':
    main()
