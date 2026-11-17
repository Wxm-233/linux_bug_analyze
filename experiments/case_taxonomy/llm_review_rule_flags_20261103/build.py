"""Collect the reviewed rule flags (criteria.md section 1, amendment 1), deduplicate them, and write one review
prompt per item (section 2). WSL; no model calls. Output: items.json and <CALLS>/Q_<nn>/prompt.md.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402

CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_rule_flags_20261103'
REVS = {'ctx': 'v6.12', 'mech': 'v6.6', 'end': 'df2908090cda'}
CTX_BASIS = {'die_rt': 'fixed_upstream', 'misaligned_uaccess': 'fixed_upstream', 'machine_shutdown': 'qemu'}
CORRECTED = {17, 22}  # amendment 1: mech_rules rows relabelled b

RULE_TEXT = {
    'CTX': '执行上下文规则：在不能睡眠的场合（关中断区间、持锁区间、陷入处理函数开中断之前、跨核调用的回调、公共代码在原子区间里调用的RISC-V钩子）调用了可能睡眠的操作；'
           '或在关中断、持raw锁、陷入处理等“硬”原子上下文中拿了PREEMPT_RT下会睡眠的普通自旋锁；或违反不可插桩（noinstr）约定。',
    'R7': '推测执行越界规则：函数对一个可能来自客体（虚拟机）或用户的下标做了上界检查，随后用它访问数组，却没有用array_index_nospec，可能被推测执行越界利用（Spectre-v1）。',
    'R10': '同一约定规则：公共代码调用、各架构各自实现的函数中，arm64、x86、LoongArch三个实现都调用了某个函数，RISC-V的实现没有。',
    'R1': '默认实现规则：公共代码中的某个默认实现，arm64、x86、LoongArch三个架构都提供了自己的版本，只有RISC-V沿用默认实现。',
    'R8': '参照修掉的写法规则：参照架构的某次修复删掉了一行写法，RISC-V的同名函数里还保留着完全相同的一行。',
}


def load(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))


def code(rev, path, name, limit=80):
    for s, e, n, t in CK.functions(rev, path):
        if n == name:
            lines = t.splitlines()
            more = len(lines) - limit
            body = '\n'.join(f'{s + k:5d}  {l}' for k, l in enumerate(lines[:limit]))
            return body + (f'\n...（其余{more}行省略）' if more > 0 else '')
    text = CK.git('show', f'{rev}:{path}').splitlines()
    for k, l in enumerate(text, 1):  # a macro or #ifndef default
        if name in l and ('#define' in l or '#ifndef' in l):
            return '\n'.join(f'{j:5d}  {text[j - 1]}' for j in range(k, min(len(text), k + 25) + 1))
    return '（未取到）'


def collect():
    items = []
    # 1. context rule, v6.12
    flags = load('ctx_rules_riscv_20261103/flags_run2.json')['flags']
    seen = set()
    for r in load('ctx_rules_riscv_20261103/manual_review.json')['rows']:
        if r['label'] not in ('a', 'b') or r['issue'] in seen:
            continue
        seen.add(r['issue'])
        f = flags[r['i']]
        items.append({'src': 'ctx', 'rule': 'CTX', 'label': r['label'], 'basis': CTX_BASIS.get(r['issue'], 'first_annotator'),
                      'path': f['path'], 'name': f['function'], 'reason': f'{f["kind"]} {f["source"]}: line {f["line"]} {f["call"]} -> {f["sink"]}',
                      'chain': f['chain'], 'key': ('CTX', f['function'], f['call'], f['sink']), 'note': r['reason']})
    # 2. four-mechanism rules, v6.6
    mflags = load('mech_rules_riscv_20261103/flags_run2.json')['flags']
    sample = load('mech_rules_riscv_20261103/review_sample.json')
    rows = load('mech_rules_riscv_20261103/manual_review.json')['rows']
    by_i = {r['i']: r for r in rows}

    def fixed(r):  # 'same as N' inherits the referenced row's evidence
        import re
        m = re.match(r'same as (\d+)', r['reason'])
        r = by_i[int(m.group(1))] if m else r
        return any(k in r['reason'] for k in ('fixed later', 'fixed by', 'c97bf629963e'))

    for r in rows:
        label = 'b' if r['i'] in CORRECTED else r['label']
        if label not in ('a', 'b'):
            continue
        s = sample[r['i']]
        full = next((f for f in mflags if f['rule'] == s['rule'] and f['path'] == s['path'] and f['name'] == s['name']), s)
        basis = ('first_annotator_corrected' if r['i'] in CORRECTED else
                 'fixed_upstream' if label == 'a' and fixed(r)
                 else 'first_annotator')
        items.append({'src': 'mech', 'rule': s['rule'], 'label': label, 'basis': basis, 'path': s['path'], 'name': s['name'],
                      'start': s['start'], 'end': s['end'], 'reason': s['reason'], 'refs': full.get('refs'),
                      'key': (s['rule'], s['name']), 'note': r['reason']})
    # 3. version-2 rules at the end version
    eflags = load('rules_v2_forward_end_20261103/flags_end.json')['flags']
    for r in load('rules_v2_forward_end_20261103/manual_review.json')['rows']:
        if r['label'] not in ('a', 'a2', 'b'):
            continue
        f = next(x for x in eflags if x['issue'] == r['issue'])
        key = ('CTX', f['name'], f['reason'].split(' ')[4] if f['rule'] == 'CTX' else '', f['reason'].split('-> ')[-1]) \
            if f['rule'] == 'CTX' else (f['rule'], f['name'])
        items.append({'src': 'end', 'rule': f['rule'], 'label': 'a' if r['label'] in ('a', 'a2') else 'b',
                      'basis': 'qemu' if 'machine_shutdown' in r['issue'] else 'first_annotator', 'path': f['path'],
                      'name': f['name'], 'reason': f['reason'], 'chain': f.get('chain') or [], 'key': key, 'note': r['reason']})
    # deduplicate (criteria section 1), keeping the earliest round
    out, keys = [], set()
    for it in items:
        k = tuple(it['key'])
        if it['rule'] == 'CTX':
            k = ('CTX', it['name'], it['reason'].split('-> ')[-1].strip(), it['reason'].split(' ')[4] if len(it['reason'].split(' ')) > 4 else '')
        if k in keys:
            continue
        keys.add(k)
        it['key'] = list(k)
        out.append(it)
    return out


def prompt(it):
    rev = REVS[it['src']]
    parts = [f'你是Linux内核的审查助手。下面是一个程序规则在Linux内核（版本{rev}）的RISC-V代码中标出的问题。请判断它在这个版本中是不是真问题。',
             '', f'【规则】{RULE_TEXT[it["rule"]]}', '', f'【被标记的位置】{it["path"]}中的{it["name"]}', '',
             f'【程序给出的理由】{it["reason"]}']
    chain = it.get('chain') or []
    if chain:
        parts += ['', '【调用链】' + ' → '.join(f'{c[1]}（{c[0]}第{c[2]}行调用{c[3]}）' for c in chain)]
    parts += ['', f'【{it["name"]}的代码】', '```c', code(rev, it['path'], it['name']), '```']
    for c in chain[:3]:
        parts += ['', f'【{c[1]}的代码（{c[0]}）】', '```c', code(rev, c[0], c[1]), '```']
    refs = it.get('refs') or {}
    for a, p in list(refs.items())[:2]:
        p = p[0] if isinstance(p, list) else p
        parts += ['', f'【参照：{a}的{it["name"]}（{p}）】', '```c', code(rev, p, it['name'], 50), '```']
    parts += ['', '请具体检查：这条路径实际能否走到，是否有条件挡住；那个状态（关中断、持锁）在那时是否真的成立，被调函数里有没有先开中断或释放锁；'
                  '下标是否真的来自不可信的一方；这是RISC-V特有的问题，还是所有架构都一样。拿不准就回答unsure。',
              '', '最后输出一个JSON对象（不要有其他JSON）：',
              '{"verdict": "real|false_alarm|unsure", "reason": "一句话", "lines": [行号]}']
    return '\n'.join(parts) + '\n'


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    items = collect()
    for k, it in enumerate(items):
        it['dir'] = f'Q_{k:02d}'
        d = CALLS / it['dir']
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(prompt(it), encoding='utf-8', newline='\n')
    (HERE / 'items.json').write_text(json.dumps(items, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    from collections import Counter
    print(len(items), Counter((it['label'], it['basis']) for it in items), Counter((it['src'], it['rule']) for it in items))


if __name__ == '__main__':
    main()
