"""Development prompts (criteria.md section 5) for the 60 LoongArch items: the swapped prompt() text of
llm_review_expand_20261103/build.py, with the program facts and the architecture table inserted before the checking
paragraph and the output requirement replaced by the three-class verdict, the claim formats (four old ones plus
config) and the refute requirement. Refuses to run unless labels3.json matches labels3_sha256.txt.
WSL (git); no model calls. Output: items.json, step1_index.json and <CALLS>/D1_nn/prompt.md."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from facts import facts, ARCH_TABLE, ARCH_NAME  # noqa: E402

spec = importlib.util.spec_from_file_location('expand_build', HERE.parent / 'llm_review_expand_20261103' / 'build.py')
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-04' / 'llm_review_v2_dev_20261104'
ARCH = 'loongarch'
CHECK_ANCHOR = '\n\n请具体检查：'
TAIL = '''请按下面三类给出判断（拿不准就回答unsure）：
- bug：在该版本某个能选到的配置、能走到的路径下，会造成实际错误：崩溃、死锁、“在原子上下文中睡眠”一类的警告、错误数据或返回值、安全问题（含推测执行越界）。
- convention：违反内核的写法约定，或与其他架构写法不一致，但在该版本的配置和路径下不会造成实际错误。
- not_issue：标记本身不成立（路径走不到、状态不成立、已有等价处理、该版本选不到相关配置），或只是缺少某项功能或优化。

请在claims中列出你的判断所依据的、关于代码的具体事实（最多5条），程序会在该版本的代码上逐条核对。每条必须是下面5种格式之一，file写提示词中给出的文件路径：
- 函数签名是否带某个标注：{"type": "annotation", "file": "路径", "function": "函数名", "annotation": "noinstr", "present": true}
- 函数是否调用某个函数：{"type": "calls", "file": "路径", "function": "函数名", "callee": "被调函数名", "present": true}
- 函数中两个调用的先后：{"type": "order", "file": "路径", "function": "函数名", "first": "先调用的函数", "then": "后调用的函数"}
- 某个调用所在分支的条件：{"type": "condition", "file": "路径", "function": "函数名", "callee": "被调函数名", "condition": "!user_mode(regs)"}
- 该版本某架构的Kconfig是否select某个选项：{"type": "config", "arch": "ARCHNAME", "symbol": "ARCH_SUPPORTS_RT", "selected": false}

如果判为not_issue，必须在refute中写出推翻这个标记的依据：claims中某条的序号（从0开始），或【程序给出的事实】中的编号（如"F2"）。没有能核对的依据，就不要判not_issue，改判unsure。

最后输出一个JSON对象（不要有其他JSON）：
{"verdict": "bug|convention|not_issue|unsure", "reason": "一句话", "lines": [行号], "claims": [上面格式的事实], "refute": [推翻标记的依据]}'''


def prompt(r):
    E.P.REVS[r['snapshot']] = r['snapshot']
    text = E.swap(E.P.prompt({**r, 'src': r['snapshot']})).rstrip()
    assert text.count(CHECK_ANCHOR) == 1 and text.endswith(E.S1.OLD_TAIL), r['cand']
    fs = facts(r, ARCH)
    block = ['', '', '【程序给出的事实】（由程序在该版本代码上算出）'] + [f'{f["id"]}. {f["text"]}' for f in fs]
    if r['rule'] == 'CTX' and ARCH in ARCH_TABLE:
        block += ['', f'【{ARCH_NAME[ARCH]}架构事实】'] + [f'- {t}' for t in ARCH_TABLE[ARCH]]
    text = text.replace(CHECK_ANCHOR, '\n'.join(block) + CHECK_ANCHOR, 1)
    text = text[:-len(E.S1.OLD_TAIL)].rstrip()
    text = text[:text.rfind('\n')] if text.endswith('最后输出一个JSON对象（不要有其他JSON）：') else text
    return text.rstrip() + '\n\n' + TAIL.replace('ARCHNAME', ARCH) + '\n', fs


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    raw = (HERE / 'labels3.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != (HERE / 'labels3_sha256.txt').read_text(encoding='utf-8').split()[0]:
        raise SystemExit('labels3.json changed after its SHA was recorded')
    items, index = [], []
    for r in json.loads(raw.decode('utf-8'))['rows']:
        text, fs = prompt(r)
        d = CALLS / f'D1_{r["cand"]:02d}'
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
        items.append({'cand': r['cand'], 'dir': d.name, 'rule': r['rule'], 'kind': r.get('kind'), 'name': r['name'],
                      'label3': r['label3'], 'basis3': r['basis3'], 'rev': r['snapshot'], 'facts': fs})
        index.append({'dir': d.name})
    (HERE / 'items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'step1_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(len(items), 'prompts')


if __name__ == '__main__':
    main()
