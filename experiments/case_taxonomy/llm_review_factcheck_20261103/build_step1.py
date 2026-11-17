"""Step-1 prompts (criteria.md sections 1-3): the 'with facts' prompts of llm_review_facts_20261103 (H1_nn, O1_nn) with
only the output requirement replaced by the claim format. Windows or WSL; no git, no model calls.
Output: items.json and <CALLS>/S1_<dir>/prompt.md.
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_facts_20261103'
SRC = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_facts_20261103'
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_factcheck_20261103'
REVS = {'ctx': 'v6.12', 'mech': 'v6.6', 'end': 'df2908090cda'}
OLD_TAIL = '最后输出一个JSON对象（不要有其他JSON）：\n{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}'
NEW_TAIL = '''另外，请在claims中列出你的判断所依据的、关于代码的具体事实（最多5条），程序会在该版本的代码上逐条核对。每条必须是下面4种格式之一，file写提示词中给出的文件路径：
- 函数签名是否带某个标注：{"type": "annotation", "file": "路径", "function": "函数名", "annotation": "noinstr", "present": true}
- 函数是否调用某个函数：{"type": "calls", "file": "路径", "function": "函数名", "callee": "被调函数名", "present": true}
- 函数中两个调用的先后：{"type": "order", "file": "路径", "function": "函数名", "first": "先调用的函数", "then": "后调用的函数"}
- 某个调用所在分支的条件：{"type": "condition", "file": "路径", "function": "函数名", "callee": "被调函数名", "condition": "!user_mode(regs)"}

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号], "claims": [上面格式的事实]}'''


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    heldout = json.loads((PREV / 'heldout_labels.json').read_text(encoding='utf-8'))['rows']
    orig = json.loads((HERE.parent / 'llm_review_rule_flags_20261103' / 'items.json').read_text(encoding='utf-8'))
    out = []
    for it in json.loads((PREV / 'prompt_index.json').read_text(encoding='utf-8')):
        if not it['facts']:
            continue
        if it['set'] == 'heldout':
            rev = heldout[it['k']]['snapshot']
        else:
            rev = REVS[next(o for o in orig if o['dir'] == it['prev_dir'])['src']]
        text = (SRC / it['dir'] / 'prompt.md').read_text(encoding='utf-8')
        assert text.rstrip().endswith(OLD_TAIL), it['dir']
        text = text.rstrip()[:-len(OLD_TAIL)] + NEW_TAIL + '\n'
        d = CALLS / f'S1_{it["dir"]}'
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
        out.append({'base': it['dir'], 'dir': d.name, 'set': it['set'], 'rule': it['rule'], 'name': it['name'],
                    'label': it['label'], 'basis': it['basis'], 'rev': rev})
    (HERE / 'items.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(out), 'step-1 prompts')


if __name__ == '__main__':
    main()
