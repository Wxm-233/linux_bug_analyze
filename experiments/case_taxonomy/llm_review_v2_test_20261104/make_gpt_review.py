"""Blind GPT review material for the 62 test labels (labels3.json, criteria.md section 4): each item as the plain
prompt of the rule flag at its snapshot (rule, location, reason, call chain, code; LoongArch or MIPS wording as in
build.py), without program facts, labels or the output requirement, plus instructions with the label definitions of
criteria.md section 4 and an answer template. The labels stay in labels3.json, outside gpt_review/.
WSL (git); no model calls. Output: gpt_review/复核说明.md, items.md, answers_template.csv."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as T  # noqa: E402

GUIDE = '''# 复核说明：程序规则标出的问题属于哪一类

`items.md`中共{n}条。每条都是一个程序规则在某个Linux内核版本的**LoongArch**（编号以L开头）或**MIPS**（编号以M开头）代码中标出的问题，附有规则说明、位置、理由、调用链和当时的代码。

请判断每条在**它所写的那个内核版本中**属于哪一类，选一个标签：

| 标签 | 含义 |
| --- | --- |
| `bug` | 真问题：在该版本某个能选到的配置、能走到的路径下，会造成实际错误，例如崩溃、死锁、“在原子上下文中睡眠”一类的警告、错误的数据或返回值、安全问题（含推测执行越界） |
| `convention` | 违反约定：违反内核的写法约定，或与其他架构写法不一致，但在该版本的配置和路径下不会造成实际错误 |
| `not_issue` | 标记不成立：路径走不到、状态不成立、已有等价处理、该版本选不到相关配置，或只是缺少某项功能或优化 |
| `unsure` | 判断不了 |

说明：
- 请按该版本的实际配置判断。例如某架构在该版本还不能开启PREEMPT_RT时，普通自旋锁不会睡眠。
- 上游后来修过，不等于该版本一定会出错；要看该版本下能否选到会出错的配置和路径。
- 可以使用你对内核的了解，包括查看上游后来的提交。理由写一句话。

填写`answers_template.csv`，另存为`answers.csv`：保留表头和第一列，不改变行的顺序。
'''


def plain(r):
    arch = 'mips' if r['cand'].startswith('M') else 'loongarch'
    swap = T.mips_swap if arch == 'mips' else T.LA_SWAP
    T.B.E.P.REVS[r['snapshot']] = r['snapshot']
    text = swap(T.B.E.P.prompt({**r, 'src': r['snapshot']})).rstrip()
    tail = T.B.E.S1.OLD_TAIL
    assert text.endswith(tail), r['cand']
    return text[:-len(tail)].rstrip()


def main():
    out = HERE / 'gpt_review'
    if out.exists():
        raise SystemExit('preserve')
    rows = json.loads((HERE / 'labels3.json').read_text(encoding='utf-8'))['rows']
    parts = [f'# 待复核的标记（{len(rows)}条）', '']
    for r in rows:
        parts += [f'## {r["cand"]}', '', plain(r), '']
    text = '\n'.join(parts) + '\n'
    for word in ('label3', 'basis3', 'reason3', 'fixed_upstream', 'first_annotator'):
        assert word not in text, word
    out.mkdir()
    (out / 'items.md').write_text(text, encoding='utf-8', newline='\n')
    (out / '复核说明.md').write_text(GUIDE.format(n=len(rows)), encoding='utf-8', newline='\n')
    (out / 'answers_template.csv').write_text('item,label,reason\n' + ''.join(f'{r["cand"]},,\n' for r in rows),
                                             encoding='utf-8', newline='\n')
    print(len(rows), 'items', len(text), 'chars')


if __name__ == '__main__':
    main()
