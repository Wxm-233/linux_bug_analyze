"""Step 2 prompts (criteria_amendment1.md). Two subcommands, both WSL, no model calls:

  python3 build_stage2.py a   step-1 answers -> passed refs (cap 200, Random(20261104)) -> 2a prompts
                              output stage1_summary.json, stage2a_index.json, <CALLS>/s2a_<id>/prompt.md
  python3 build_stage2.py d   2a answers -> 2b candidates + 2c facts -> 2d prompts
                              output locate.json, stage2d_index.json, <CALLS>/s2d_<id>/prompt.md
"""
from concurrent.futures import ThreadPoolExecutor
import json
import random
import sys

import locate as L
from common import CALLS, CK, HERE, ROOT, git, message, parse_answer

sys.path.insert(0, str(ROOT / 'mech_scan_riscv_20261102'))
import modules as MOD  # noqa: E402  (mechanism modules shared with the scan line)

CATALOG = (ROOT / 'cross_arch_sample_set_20261102' / 'catalog_v2.md').read_text(encoding='utf-8')
CAP = 200

A_TEMPLATE = '''你是Linux内核跨架构问题的分析助手。下面是一个arm64、x86或LoongArch上的修复或公共改动。请把它拆解成几项要素，供后续在RISC-V上核对。

需要拆出：
- condition：原来的代码在什么条件下出错（或公共改动之后，什么条件下各架构的实现必须改变）；
- guarantee：修复补上的保证是什么（例如加了某个判断、调整了先后顺序、加了屏障、改为原子操作、换了执行上下文、改了宽度或对齐、补了释放、改了配置依赖）；
- kind：保证的类别，取check、order、barrier、atomic、context、width、lifetime、config、other之一；
- hooks：涉及的函数名，包括公共代码调用、各架构各自实现的函数（钩子），以及公共代码中直接相关的函数；只写函数名；
- mechanism：按下面的机制目录选一个代号。

只根据材料判断，最后输出一个JSON对象（不要有其他JSON）：
{{"condition": "...", "guarantee": "...", "kind": "...", "hooks": ["..."], "mechanism": "M?"}}

【机制目录】
{catalog}

【标题】
{subject}

【提交说明】
{message}

【改动】
{diff}
'''

D_TEMPLATE = '''你是Linux内核跨架构问题的分析助手。其他架构上有一个修复（或公共改动），已拆解为：
- 出错条件C：{condition}
- 补上的保证G：{guarantee}
- 类别：{kind}

程序按“同一钩子”“同一公共调用者”“标识符检索”三条路线，在当时的RISC-V代码中找到了下面的候选函数，并列出了每个候选中的调用及其路径条件。

请对每个候选回答两个问题：
1. applies：条件C在这个RISC-V函数里是否适用（这个函数是否承担与参照修复相同的要求）？
2. guarantee_provided：若适用，这里有没有提供保证G？

要求：
- 必须引用候选函数中的行号（下面代码前的数字）作为依据；
- 只判断这些候选；如果你认为对应位置在候选之外，写在elsewhere里，不要写进verdicts；
- 拿不准就回答unsure。

最后输出一个JSON对象（不要有其他JSON）：
{{"verdicts": [{{"candidate": "文件:函数", "applies": "yes|no|unsure", "guarantee_provided": "yes|no|unsure", "lines": [行号], "why": "一句话"}}], "elsewhere": "候选以外可能的位置，或空字符串"}}

【参照修复的标题】
{subject}

【参照修复的改动（节选）】
{diff}

【RISC-V候选】
{cands}
'''


def diff_of(sha, limit):
    lines = git('show', '--format=', '-U3', sha).splitlines()
    more = f'\n...（其余{len(lines) - limit}行省略）' if len(lines) > limit else ''
    return '\n'.join(lines[:limit]) + more


def stage_a():
    refs = {r['id']: r for r in json.loads((HERE / 'refs.json').read_text(encoding='utf-8'))}
    counts, passed, missing = {'yes': 0, 'no': 0, 'unsure': 0}, [], []
    for rid in refs:
        a = parse_answer(CALLS / f's1_{rid}')
        v = (a or {}).get('shared')
        if v not in counts:
            missing.append(rid)
            continue
        counts[v] += 1
        if v in ('yes', 'unsure'):
            passed.append(rid)
    chosen = sorted(random.Random(20261104).sample(sorted(passed), CAP)) if len(passed) > CAP else sorted(passed)
    (HERE / 'stage1_summary.json').write_text(json.dumps(
        {'refs': len(refs), 'answers': counts, 'no_answer': missing, 'passed': len(passed), 'chosen': chosen},
        indent=1) + '\n', encoding='utf-8')
    index = []
    for rid in chosen:
        d = CALLS / f's2a_{rid}'
        d.mkdir()
        r = refs[rid]
        (d / 'prompt.md').write_text(A_TEMPLATE.format(catalog=CATALOG, subject=r['subject'], message=message(r['sha']),
                                                       diff=diff_of(r['sha'], 300)), encoding='utf-8', newline='\n')
        index.append({'dir': d.name, 'id': rid})
    (HERE / 'stage2a_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(counts, 'no answer', len(missing), 'passed', len(passed), 'chosen', len(chosen))


def numbered(c):
    return '\n'.join(f'{c["start"] + k:5d}  {line}' for k, line in enumerate(c['text'].splitlines()))


FOCUS = {
    'M1': '本条按机制M1（默认假设不适用）核对：候选是公共代码中的默认实现，RISC-V没有提供自己的版本而直接使用它。'
          'applies问“默认实现的假设是否涉及条件C”；guarantee_provided问“对RISC-V而言默认实现是否满足保证G”'
          '（考虑RISC-V的特点：页表级数运行时可变、NAPOT多项大页、压缩指令、弱内存模型、XLEN 32/64、指令缓存不一致、经SBI访问固件）。'
          '行号引用默认实现中的行。',
    'M5': '本条按机制M5（执行上下文）核对：先确定每个候选运行在什么上下文（关中断、异常入口、noinstr等），'
          '再看其中有没有可能睡眠、被插桩、迁移CPU或依赖已关闭机制的调用，以及有没有参照修复补上的那种处理。',
    'M8': '本条按机制M8（落后于参照对象的演进）核对：候选是参照修复所改函数在RISC-V中的同名函数。'
          'applies问“RISC-V这个函数是否承担参照修复所针对的要求”；guarantee_provided问“RISC-V是否已有与参照修复等价的处理”。',
    'M10': '本条按机制M10（同一约定、各自实现）核对：候选是同一个公共钩子在RISC-V中的实现，下面列出了参照架构修复后有、'
           'RISC-V没有的调用。applies问“这条约定是否要求这些调用或判断”；guarantee_provided问“RISC-V是否以别的方式满足了”。',
}


def mech_of(a):
    m = str(a.get('mechanism', '')).strip().upper()
    return m if m in ('M1', 'M2', 'M5', 'M8', 'M10') else 'generic'


def m1_candidates(sha, names, rev):
    """Defaults among `names` that RISC-V does not override (criteria_amendment3.md, M1 row)."""
    defaults = {n: (p, k) for n, p, k in MOD.m1_defaults(rev) if n in set(names)}
    rv = MOD.defs_in(rev, list(defaults), ('arch/riscv/*.c', 'arch/riscv/*.h', 'drivers/acpi/riscv/*.c'), macros=True)
    out = []
    for n, (p, _) in defaults.items():
        if n in rv:
            continue
        f = MOD.function(rev, p, n)
        if f:
            out.append({'route': 'M1', **f})
    return out


def m8_candidates(sha, changed, rev):
    names = [n for p, n in changed if p.startswith(L.REF_PREFIXES) and p.endswith('.c') and n not in L.GENERIC]
    out = []
    for n, paths in L.definitions(rev, names, ('arch/riscv/*.c',)).items():
        f = MOD.function(rev, paths[0], n)
        if f:
            ref_path = next(p for p, m in changed if m == n)
            after = MOD.function(sha, ref_path, n)
            f['extra'] = f'【参照修复之后的{ref_path}:{n}】\n' + (numbered(after) if after else '（未取到）')
            out.append({'route': 'M8', **f})
    return out


def m10_candidates(sha, changed, hooks, rev):
    names = list(dict.fromkeys([n for _, n in changed] + list(hooks)))
    rv = L.definitions(rev, names)
    out = []
    for n, paths in rv.items():
        refs = [(p, m) for p, m in changed if m == n and p.startswith(L.REF_PREFIXES)]
        f = MOD.function(rev, paths[0], n)
        if not f or not refs:
            continue
        after = MOD.function(sha, refs[0][0], n)
        if not after:
            continue
        missing = sorted(MOD.call_names(after['text']) - MOD.call_names(f['text']) - {n})
        missing = [c for c in missing if not MOD.ARCH_WORDS.search(c)]
        f['extra'] = (f'【参照架构修复后的实现 {refs[0][0]}】\n{numbered(after)}\n'
                      f'【参照修复后有、RISC-V没有的调用】{", ".join(missing) or "（无）"}')
        out.append({'route': 'M10', **f})
    return out


def locate_one(r):
    a = parse_answer(CALLS / f's2a_{r["id"]}') or {}
    hooks = [h for h in a.get('hooks') or [] if isinstance(h, str)] if isinstance(a.get('hooks'), list) else []
    mech = mech_of(a)
    try:
        c = L.candidates(r['sha'], hooks)
        rev = c['rev']
        changed, _ = L.ref_changes(r['sha'])
        special = []
        if mech == 'M1':
            special = m1_candidates(r['sha'], [n for _, n in changed] + hooks, rev)
        elif mech == 'M8':
            special = m8_candidates(r['sha'], changed, rev)
        elif mech == 'M10':
            special = m10_candidates(r['sha'], changed, hooks, rev)
        elif mech == 'M2':
            keys = {(p['path'], p['name']) for p in c['picked']}
            c['rule_flags'] = [x for x in CK.check(rev, 'riscv') if x['verdict'] in ('strong', 'weak')
                               and (x['file'], x['function']) in keys]
        c['dispatch'] = mech if (special or mech in ('M2', 'M5')) else 'generic'
        if special:
            c['all_candidates'] = [{'route': s['route'], 'path': s['path'], 'name': s['name']} for s in special] + \
                c['all_candidates']
            c['picked'] = special[:L.MAX_FUNCS]
    except Exception as exc:  # recorded, not retried
        return r['id'], a, {'error': repr(exc)[:300]}
    for p in c['picked']:
        p['facts'], p['irq_region_calls'] = L.facts(p)
    return r['id'], a, c


def stage_d():
    refs = {r['id']: r for r in json.loads((HERE / 'refs.json').read_text(encoding='utf-8'))}
    chosen = json.loads((HERE / 'stage1_summary.json').read_text(encoding='utf-8'))['chosen']
    with ThreadPoolExecutor(max_workers=8) as pool:
        located = list(pool.map(locate_one, [refs[i] for i in chosen]))
    store, index = {}, []
    for rid, a, c in located:
        store[rid] = {'stage2a': a, **c}
        if 'error' in c or not c['picked'] or c.get('dispatch') == 'M2':
            continue
        blocks = []
        for p in c['picked']:
            facts = '\n'.join(p['facts']) or '（无调用）'
            irq = '\n'.join(p['irq_region_calls']) or '（无）'
            blocks.append(f'=== 候选：{p["path"]}:{p["name"]}（路线{p["route"]}，第{p["start"]}–{p["end"]}行）\n'
                          f'【代码】\n{numbered(p)}\n【调用及路径条件】\n{facts}\n【关中断区间内的调用】\n{irq}\n'
                          + (p.get('extra', '') + '\n'))
        focus = FOCUS.get(c.get('dispatch'), '')
        d = CALLS / f's2d_{rid}'
        d.mkdir()
        (d / 'prompt.md').write_text(D_TEMPLATE.format(
            condition=a.get('condition', '（未拆出）'), guarantee=a.get('guarantee', '（未拆出）'),
            kind=a.get('kind', 'other'), subject=refs[rid]['subject'], diff=diff_of(refs[rid]['sha'], 120),
            cands=('【机制要点】\n' + focus + '\n\n' if focus else '') + '\n'.join(blocks)),
            encoding='utf-8', newline='\n')
        index.append({'dir': d.name, 'id': rid, 'dispatch': c.get('dispatch')})
    (HERE / 'locate.json').write_text(json.dumps(store, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'stage2d_index.json').write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    print(len(chosen), 'chosen', len(index), 'with candidates')


if __name__ == '__main__':
    {'a': stage_a, 'd': stage_d}[sys.argv[1]]()
