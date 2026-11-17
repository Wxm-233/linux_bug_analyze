"""Prompts for L, the model review of the patch itself (criteria.md section 4): P step4, P step8 and U step3, three
runs each. Each prompt holds the cumulative change of the version against its base (arch/riscv, kernel, include),
the arch/x86 part of the reference commits, the full text of every changed function after the change, the
mechanism checklist and this round's P1-P3 output on the changed functions. Needs results/ from run.py.
WSL (git); no model calls. Output: <CALLS>/L_<series>_<tag>_r<k>/prompt.md and review_index.json.
"""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(HERE.parent / 'patch_check_20261105'))
import checker as CK  # noqa: E402
import patch_check as PC  # noqa: E402  (changed_functions)

CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-05' / 'patch_rules_20261105'
STATES = [('P', 'step4'), ('P', 'step8'), ('U', 'step3')]
RUNS = 3
MAX_DIFF = 900

CHECKLIST = """按机制逐项检查（每一项都要看，没有问题的写“未发现”）：

1. **M5 执行上下文，正方向**：在关中断、关抢占、持自旋锁或在中断处理中，是否调用了会睡眠的函数（加互斥锁、`GFP_KERNEL`分配、`vmalloc`、访问用户内存等）。
2. **M5 执行上下文，反方向**：只在当前CPU上生效的操作（fixmap映射、本核TLB刷新、本核指令缓存刷新、per-CPU数据），是否在不会被迁移到别的CPU的上下文中进行（关抢占、关中断，或在`stop_machine`回调中）。
3. **M10 同一约定，变体完整性**：RISC-V有RV64和RV32两个变体。公共代码或两个变体共用的文件需要的钩子，两个变体是否都实现了；没有实现时，公共代码的`__weak`默认实现是否会让功能出错。
4. **M10 同一约定，与参照补丁对应**：参照架构（x86）补丁中的每处关键处理，在RISC-V补丁中是否有对应；没有对应的，判断RISC-V是否确实不需要。
5. **M10 同一约定，地址与语义一致**：这个功能区分“可写的构造缓冲区”和“可执行的运行映像”两套地址。凡是在运行时才用到的地址（跳转和调用的目标、PC相对计算、异常表、`prog->bpf_func`、之后要释放或改写的指针等），是否都取自可执行的运行映像；凡是写入，是否都写到可写缓冲区。
6. **M3 映射步骤与指令缓存**：改写代码后，是否按RISC-V的要求刷新了指令缓存（包括其他CPU）；映射建立、使用、拆除的步骤是否完整。
7. **M6 资源生命周期**：分配的内存、映射和pack在出错路径和释放路径上，是否都被正确释放且只释放一次；申请大块内存的地方，失败时是否有合理的退路。
8. **其他**：以上没有覆盖、但你认为会导致错误的问题。"""

TEMPLATE = """# 任务：审查一组RISC-V迁移补丁

下面是一组把BPF prog_pack功能迁移到RISC-V的补丁（相对基线的累计改动），以及参照架构x86上同一功能的上游补丁。请按机制逐项检查这组RISC-V补丁中的错误。

要求：
- 只报告你能用代码说明的问题，并引用具体的行；
- 不要因为“风格不同”或“可以更好”就报告，只报告会导致错误的问题：编译失败、运行出错、行为与参照架构不一致而造成错误、资源泄漏、内核警告；
- 每个问题写明是否需要运行才能确认；
- 程序检查（P1–P3）的结果附在后面，只作参考，它们可能有误报，也可能漏报。

{checklist}

## 输出格式

先按上面8项逐项写简短结论，然后输出一个JSON代码块：

```json
[{{"位置": "文件:函数", "机制": "M5/M10/M3/M6/其他", "检查项": 1, "问题": "一句话", "依据": "引用代码行并说明", "需要运行确认": true}}]
```

没有问题时输出`[]`。

## 一、RISC-V补丁（相对基线`{base}`的累计改动）

```diff
{diff}
```

## 二、改动后的完整函数

{functions}

## 三、参照补丁（x86部分）

{reference}

## 四、程序检查结果（P1–P3，只作参考）

{checks}
"""


def ref_text():
    out = []
    for line in (HERE / 'input' / 'reference_x86.txt').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        c = line.split()[0]
        diff = CK.git('show', '--format=%h %s', c, '--', 'arch/x86').rstrip()
        if '\n' in diff:
            out.append('```diff\n' + diff + '\n```')
    return '\n\n'.join(out)


def checks_text(series, tag, changed):
    d = json.loads((HERE / 'results' / f'flags_{series}_{tag}.json').read_text(encoding='utf-8'))
    names = {n for _, n in changed}
    rows = []
    for f in d['flags']:
        on_patch = ({f['name'], *f.get('chain', [])} & names) if f['rule'] == 'P1' else \
            (f['name'] in names or f['path'] in {p for p, _ in changed})
        if on_patch:
            rows.append(f'- {f["rule"]} `{f["path"]}:{f["name"]}`：{f["reason"]}')
    p3 = HERE / 'results' / f'p3_{series}_{tag}.json'
    if p3.exists():
        miss = [r for r in json.loads(p3.read_text(encoding='utf-8'))['rows'] if not r['found']]
        rows += [f'- P3 参照补丁（{r["reference"]}）中的{"钩子" if r["kind"] == "hook" else "公共接口调用"}`{r["name"]}`，'
                 f'RISC-V补丁中没有对应' for r in miss]
    return '\n'.join(rows) or '（无）'


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    ref = ref_text()
    index = []
    for series, tag in STATES:
        cj = json.loads((HERE.parent / 'patch_check_20261105' / 'results' / series / 'commits.json')
                        .read_text(encoding='utf-8'))
        sha = next(s['sha'] for s in cj['steps'] if f'step{s["step"]}' == tag)
        diff = CK.git('diff', cj['base'], sha, '--', 'arch/riscv', 'kernel', 'include').splitlines()
        if len(diff) > MAX_DIFF:
            raise SystemExit(f'{series} {tag}: diff has {len(diff)} lines, more than {MAX_DIFF}')
        changed = PC.changed_functions(cj['base'], sha)
        funcs = []
        for path, name in sorted(changed):
            t = next((t for s, e, n, t in CK.functions(sha, path) if n == name), None)
            if t:
                funcs.append(f'### `{path}:{name}`\n\n```c\n{t}\n```')
        text = TEMPLATE.format(checklist=CHECKLIST, base=cj['base'][:12], diff='\n'.join(diff),
                               functions='\n\n'.join(funcs), reference=ref,
                               checks=checks_text(series, tag, changed))
        assert 'Fixes:' not in text and 'a370c2419e46' not in text
        for k in range(1, RUNS + 1):
            d = CALLS / f'L_{series}_{tag}_r{k}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'series': series, 'tag': tag, 'run': k, 'chars': len(text)})
    (HERE / 'review_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(json.dumps([(x['dir'], x['chars']) for x in index]))


if __name__ == '__main__':
    main()
