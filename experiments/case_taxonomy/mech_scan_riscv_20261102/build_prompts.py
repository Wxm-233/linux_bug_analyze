"""Narrow-question prompts for each check point (criteria.md sections 2-3): at most 250 points per model module
(Random(20261105)); M2 needs no model. WSL; no model calls. Output: <CALLS>/<module>_<nnn>/prompt.md and
prompt_index.json (with each point and the line range a cited line must fall in).
"""
from pathlib import Path
import json
import random
import re

import modules as M

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-02' / 'mech_scan_20261102'
SNAP, CAP = 'v6.12', 250
RISCV_TRAITS = ('页表级数在运行时可变（Sv39/48/57）；NAPOT用多个页表项拼成大页；压缩指令（2字节）；弱内存模型；'
                'XLEN为32或64；指令缓存与数据缓存不一致；经SBI访问固件')
HEAD = '你是Linux内核跨架构问题的分析助手。以下材料取自内核v6.12。只根据材料和你对内核的了解判断，拿不准就回答unsure。\n\n'
TAIL = '\n最后输出一个JSON对象（不要有其他JSON）：\n{schema}\n'


def numbered(f, limit=None):
    lines = f['text'].splitlines()
    more = len(lines) - limit if limit and len(lines) > limit else 0
    lines = lines[:limit] if limit else lines
    return '\n'.join(f'{f["start"] + k:5d}  {l}' for k, l in enumerate(lines)) + (f'\n...（其余{more}行省略）' if more else '')


def block(path, lines_from, lines_to=None, limit=40):
    """Numbered source lines of path at SNAP."""
    text = M.git('show', f'{SNAP}:{path}').splitlines()
    end = min(len(text), (lines_to or lines_from + limit - 1))
    return '\n'.join(f'{k:5d}  {text[k - 1]}' for k in range(lines_from, end + 1)), (lines_from, end)


def m1(p):
    path = p['default_path']
    f = M.function(SNAP, path, p['name'])
    if f:
        body, rng = numbered(f, 60), (f['start'], f['end'])
    else:
        text = M.git('show', f'{SNAP}:{path}').splitlines()
        k = next((i for i, l in enumerate(text, 1) if re.match(r'#\s*ifndef\s+' + p['name'] + r'\s*$', l)), 1)
        e = next((i for i, l in enumerate(text[k:], k + 1) if l.startswith('#endif')), k + 20)
        body, rng = block(path, k, min(e, k + 40))
    a = p['overridden_by'][0]
    rp = p['ref_paths'][a][0]
    rf = M.function(SNAP, rp, p['name'])
    if rf:
        ref = numbered(rf, 60)
    else:
        t = M.git('show', f'{SNAP}:{rp}').splitlines()
        k = next((i for i, l in enumerate(t, 1) if re.search(r'#\s*define\s+' + p['name'] + r'\b', l)), 1)
        ref, _ = block(rp, k, k + 15)
    uses = M.git('grep', '-n', '-w', p['name'], SNAP, '--', 'arch/riscv').splitlines()[:10]
    uses = '\n'.join(u.split(':', 1)[1] for u in uses) or '（RISC-V中没有直接出现这个名字）'
    prompt = (HEAD + f'''公共代码中有一个可由架构覆盖的默认实现`{p["name"]}`（{path}）。{a}提供了自己的版本，RISC-V没有提供，因此RISC-V使用默认实现。

请回答：
1. 默认实现对架构做了什么假设？
2. {a}为什么要提供自己的版本？
3. RISC-V在下列方面的特点，会不会让这个假设不成立：{RISCV_TRAITS}？若成立就回答violated为no。
必须引用默认实现中的行号。

【默认实现】
{body}

【{a}的版本（{rp}）】
{ref}

【RISC-V中出现这个名字的位置】
{uses}
''' + TAIL.format(schema='{"assumption": "一句话", "why_ref_overrides": "一句话", "violated": "yes|no|unsure", '
                       '"lines": [行号], "why": "一句话"}'))
    return prompt, {'path': path, 'range': rng, 'verdict_key': 'violated'}


SLEEP_NOTE = ('可能睡眠或不允许的调用包括：互斥锁与读写信号量、等待与调度、带GFP_KERNEL的分配、vmalloc、'
              '用户内存访问（copy_from_user等可能缺页）、跨核调用并等待；在PREEMPT_RT下spin_lock也会睡眠；'
              'noinstr函数中不应调用可被插桩的函数。')


def m5(p):
    f = M.function(SNAP, p['path'], p['name'])
    rows, irq = M.facts(f)
    flagged = [f'第{ln}行 {c}' for ln, c in irq if M.SLEEP.fullmatch(c)]
    ctx = []
    if p['marks']:
        ctx.append('标注' + '、'.join(p['marks']))
    if p['irq_region']:
        ctx.append('含关中断区间')
    if p['entry']:
        ctx.append('异常处理入口')
    prompt = (HEAD + f'''下面是RISC-V函数`{p["name"]}`（{p["path"]}）。程序判断它与执行上下文有关：{'；'.join(ctx)}。
{SLEEP_NOTE}

请回答：这个函数（或其中的某段）运行在什么上下文？在这个上下文中，有没有调用可能睡眠、可能被插桩、可能迁移CPU或依赖已关闭机制的函数？必须引用函数中的行号。

【代码】
{numbered(f, 150)}

【调用及路径条件（程序列出）】
{chr(10).join(rows) or '（无调用）'}

【关中断区间内的调用】
{chr(10).join(f'第{ln}行 {c}' for ln, c in irq) or '（无）'}

【其中在“可能睡眠”清单中的】
{chr(10).join(flagged) or '（无）'}
''' + TAIL.format(schema='{"context": "一句话", "violation": "yes|no|unsure", "lines": [行号], "why": "一句话"}'))
    return prompt, {'path': p['path'], 'range': (f['start'], f['end']), 'verdict_key': 'violation'}


def m8(p):
    f = M.function(SNAP, p['path'], p['name'])
    a = M.function(SNAP, p['arm64_path'], p['name'])
    fixes = []
    for x in p['arm64_fixes'][:4]:
        msg = '\n'.join(M.git('log', '-1', '--format=%B', x['sha']).splitlines()[:20])
        diff = '\n'.join(M.git('show', '--format=', x['sha'], '--', p['arm64_path']).splitlines()[:60])
        fixes.append(f'--- arm64修复 {x["sha"]}（{x["date"]}）\n{msg}\n{diff}')
    prompt = (HEAD + f'''RISC-V和arm64都有函数`{p["name"]}`。RISC-V的版本最后一次修改是{p["riscv_last_change"]}；之后arm64的同名函数被下列修复改过。

请回答：这些arm64修复中，有没有修的是RISC-V同样承担的要求、而RISC-V的`{p["name"]}`还没有相应处理？若有，指出是哪一个修复，并引用RISC-V函数中的行号；若这些修复只与arm64自己的硬件或功能有关，回答no。

【RISC-V：{p["path"]}】
{numbered(f, 120)}

【arm64（v6.12中）：{p["arm64_path"]}】
{numbered(a, 120) if a else '（未取到）'}

【arm64在RISC-V最后修改之后的修复】
{chr(10).join(fixes)}
''' + TAIL.format(schema='{"needs_same_fix": "yes|no|unsure", "fix": "arm64修复的提交号或空", "lines": [行号], '
                       '"why": "一句话"}'))
    return prompt, {'path': p['path'], 'range': (f['start'], f['end']), 'verdict_key': 'needs_same_fix'}


def m10(p):
    f = M.function(SNAP, p['path'], p['name'])
    refs = []
    for a, rp in list(p['refs'].items())[:2]:
        rf = M.function(SNAP, rp, p['name'])
        conds = [f'{c.name}：' + (' 且 '.join(e if pos else f'非({e})' for e, pos in c.conds) or '无条件')
                 for c in M.analyze(rf['text']) if c.name in p['missing']]
        refs.append(f'【{a}：{rp}】\n{numbered(rf, 80)}\n【其中RISC-V没有的调用及条件】\n' + '\n'.join(conds[:15]))
    prompt = (HEAD + f'''`{p["name"]}`由公共代码调用、各架构各自实现。程序比较了各架构的实现，发现下列调用在至少两个参照架构的实现里都有，而RISC-V的实现里没有：{', '.join(p["missing"][:20])}。

请回答：这些RISC-V没有的调用或判断，是这条约定的要求（RISC-V也应该有），还是参照架构自己的需要（RISC-V不需要）？若是约定的要求，指出缺的是哪一个，并引用RISC-V实现中的行号（缺失处附近的行）。

【RISC-V：{p["path"]}】
{numbered(f, 80)}

{chr(10).join(refs)}
''' + TAIL.format(schema='{"contract_violation": "yes|no|unsure", "missing": "缺的调用或判断", "lines": [行号], '
                       '"why": "一句话"}'))
    return prompt, {'path': p['path'], 'range': (f['start'], f['end']), 'verdict_key': 'contract_violation'}


BUILD = {'M1': m1, 'M5': m5, 'M8': m8, 'M10': m10}


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    pts = json.loads((HERE / 'points.json').read_text(encoding='utf-8'))['points']
    index, sampled = [], {}
    for mod, fn in BUILD.items():
        ps = pts[mod]
        chosen = ps if len(ps) <= CAP else random.Random(20261105).sample(ps, CAP)
        sampled[mod] = [len(chosen), len(ps)]
        for k, p in enumerate(chosen):
            try:
                prompt, meta = fn(p)
            except Exception as exc:  # recorded, the point is skipped
                index.append({'dir': None, 'module': mod, 'point': p, 'error': repr(exc)[:200]})
                continue
            d = CALLS / f'{mod}_{k:03d}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(prompt, encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'module': mod, 'point': p, **meta})
    (HERE / 'prompt_index.json').write_text(json.dumps({'sampled': sampled, 'items': index}, indent=1,
                                                       ensure_ascii=False) + '\n', encoding='utf-8')
    print(sampled, sum(1 for x in index if x.get('dir')), 'prompts', sum('error' in x for x in index), 'errors')


if __name__ == '__main__':
    main()
