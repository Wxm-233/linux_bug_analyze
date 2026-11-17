"""Context facts (criteria.md section 2) for the 77 cases of judge_bench_dev_20261103 and the V2 prompts: the V0
prompt text unchanged plus one question sentence and one context section (section 3). WSL; no model calls.
Output: context.json, prompt_index.json and <CALLS>/V2_<case>/prompt.md.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
import modules as M  # noqa: E402
from modules import analyze, function  # noqa: E402

DEV = HERE.parent / 'judge_bench_dev_20261103'
V0_CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_sonnet_20261103'
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_context_20261103'
MARKS = ('__init', '__exit', 'noinstr', '__cpuidle', '__kprobes', 'notrace', '__ref')
ACQUIRE = re.compile(r'(raw_)?spin_lock\w*|(raw_)?read_lock\w*|(raw_)?write_lock\w*|mutex_lock\w*|rcu_read_lock\w*|'
                     r'preempt_disable\w*|local_bh_disable|cpus_read_lock|cpu_hotplug_disable|stop_machine\w*|'
                     r'down_(read|write)\w*')
RELEASE = {'spin_unlock': 'spin_lock', 'read_unlock': 'read_lock', 'write_unlock': 'write_lock',
           'mutex_unlock': 'mutex_lock', 'rcu_read_unlock': 'rcu_read_lock', 'preempt_enable': 'preempt_disable',
           'local_bh_enable': 'local_bh_disable', 'cpus_read_unlock': 'cpus_read_lock',
           'cpu_hotplug_enable': 'cpu_hotplug_disable', 'up_read': 'down_read', 'up_write': 'down_write'}
KEYWORDS = re.compile(r'Context|must|lock|sleep|irq|interrupt|order|barrier|atomic|Return', re.I)
SPEC = ['*.c', '*.h', ':(exclude)tools', ':(exclude)Documentation'] + \
       [f':(exclude)arch/{a}' for a in ('alpha', 'arc', 'arm', 'arm64', 'csky', 'hexagon', 'loongarch', 'm68k',
                                        'microblaze', 'mips', 'nios2', 'openrisc', 'parisc', 'powerpc', 's390', 'sh',
                                        'sparc', 'um', 'x86', 'xtensa')]


def git(*a):
    return M.git(*a)


def enclosing(rev, path, line):
    for s, e, n, t in M.funcs(rev, path):
        if s - 8 <= line <= e:
            return {'path': path, 'name': n, 'start': s, 'end': e, 'text': t}
    return None


def marks_of(f):
    head = f['text'].split('{', 1)[0]
    return [m for m in MARKS if re.search(r'(^|\W)' + m + r'(\W|$)', head)]


def state_at(f, line, name):
    """(inside irq-off region, held locks, path condition) of the call to `name` at file line `line`."""
    calls = analyze(f['text'])
    irq, held, cond = False, [], None
    for c in calls:
        at = f['start'] + c.line - 1
        if at >= line and c.name == name:
            cond = ' 且 '.join(e if pos else f'非({e})' for e, pos in c.conds) or '无条件'
            cond = cond if len(cond) <= 200 else cond[:200] + '…（截断）'
            break
        if at >= line:
            break
        if M.DISABLE.fullmatch(c.name):
            irq = True
        elif M.ENABLE.fullmatch(c.name):
            irq = False
        elif ACQUIRE.fullmatch(c.name):
            held.append(c.name)
        else:
            base = re.sub(r'^raw_|_irq\w*$|_bh$|_nested$', '', c.name)
            for rel, acq in RELEASE.items():
                if base == rel:
                    for k in range(len(held) - 1, -1, -1):
                        if acq in held[k]:
                            del held[k]
                            break
    return irq, held, cond


def callers(rev, fn):
    hits = git('grep', '-n', '-w', fn['name'], rev, '--', *SPEC).splitlines()
    sites, ptrs = [], []
    for h in hits:
        parts = h.split(':', 3)
        if len(parts) < 4:
            continue
        path, line, text = parts[1], int(parts[2]), parts[3]
        if path == fn['path'] and fn['start'] - 8 <= line <= fn['end']:
            continue
        if re.search(r'(\.\w+\s*=|=)\s*&?' + re.escape(fn['name']) + r'\s*[,;]', text):
            m = re.search(r'\.(\w+)\s*=', text)
            ptrs.append(f'{path}:{line}: {text.strip()}' + (f'（字段 {m.group(1)}）' if m else ''))
            continue
        if not re.search(r'(^|[^A-Za-z0-9_])' + re.escape(fn['name']) + r'\s*\(', text):
            continue
        if path.endswith('.h') and re.match(r'\s*(extern\s+)?[\w\s\*]+\b' + re.escape(fn['name']) + r'\s*\(.*\)\s*;', text):
            continue
        sites.append((path, line))
    sites.sort(key=lambda x: (not x[0].startswith('arch/riscv'), x))
    rows = []
    for path, line in sites[:8]:
        f = enclosing(rev, path, line)
        if not f:
            rows.append({'site': f'{path}:{line}', 'caller': None})
            continue
        irq, held, cond = state_at(f, line, fn['name'])
        up = []
        for h in git('grep', '-n', '-w', f['name'], rev, '--', *SPEC).splitlines()[:40]:
            p = h.split(':', 3)
            if len(p) < 4 or (p[1] == f['path'] and f['start'] - 8 <= int(p[2]) <= f['end']):
                continue
            if not re.search(r'(^|[^A-Za-z0-9_])' + re.escape(f['name']) + r'\s*\(', p[3]):
                continue
            g = enclosing(rev, p[1], int(p[2]))
            if g and g['name'] not in [u['name'] for u in up]:
                up.append({'name': g['name'], 'path': p[1], 'marks': marks_of(g)})
            if len(up) == 4:
                break
        rows.append({'site': f'{path}:{line}', 'caller': f['name'], 'marks': marks_of(f), 'irq_off': irq,
                     'held': held, 'cond': cond, 'up': up})
    return rows, len(sites), ptrs[:4], len(ptrs)


def doc_before(rev, path, line, limit=12):
    """The comment block that ends right above `line` (1-based), or None."""
    text = git('show', f'{rev}:{path}').splitlines()
    k = line - 2
    while k >= 0 and text[k].strip() == '':
        k -= 1
    if k < 0 or not text[k].strip().endswith('*/'):
        return None
    end = k
    while k >= 0 and '/*' not in text[k]:
        k -= 1
    if k < 0:
        return None
    block = text[k:end + 1]
    return block, text[k].lstrip().startswith('/**')


def hook_doc(rev, fn):
    for h in git('grep', '-n', '-E', r'(^|[^A-Za-z0-9_])' + fn['name'] + r'[[:space:]]*\(', rev, '--',
                 'include/').splitlines():
        p = h.split(':', 3)
        if len(p) < 4:
            continue
        d = doc_before(rev, p[1], int(p[2]))
        if d:
            return {'where': f'{p[1]}:{p[2]}', 'text': '\n'.join(d[0][:12])}
    return None


def api_docs(rev, fn):
    names = sorted({c.name for c in analyze(fn['text'])} - {fn['name']})
    where = ['include/', 'kernel/', 'mm/', 'lib/', 'drivers/', 'fs/', 'net/', 'block/', 'init/', 'virt/', 'security/']
    found = M.defs_in(rev, names, where, macros=True)
    out = []
    for n in names:
        for path in sorted(found.get(n, []), key=lambda p: not p.startswith('include/')):
            for h in git('grep', '-n', '-E', r'(^[A-Za-z_].*[^A-Za-z0-9_]' + n + r'[[:space:]]*\()|(^#[[:space:]]*define[[:space:]]+'
                         + n + r'([^A-Za-z0-9_]|$))', rev, '--', path).splitlines()[:3]:
                p = h.split(':', 3)
                d = doc_before(rev, path, int(p[2])) if len(p) == 4 else None
                if d and d[1]:
                    text = '\n'.join(d[0][:12])
                    out.append({'name': n, 'where': f'{path}:{p[2]}', 'hits': len(KEYWORDS.findall(text)),
                                'text': text})
                    break
            if out and out[-1]['name'] == n:
                break
    out.sort(key=lambda x: (-x['hits'], x['name']))
    return out[:6], len(out)


def context(case):
    rev, t = case['rev'], case['target']
    fn = function(rev, t['path'], t['name'])
    rows, n_sites, ptrs, n_ptrs = callers(rev, fn)
    docs, n_docs = api_docs(rev, fn)
    return {'id': case['id'], 'callers': rows, 'call_sites': n_sites, 'pointers': ptrs, 'pointer_sites': n_ptrs,
            'hook_doc': hook_doc(rev, fn), 'api_docs': docs, 'api_docs_found': n_docs}


def render(c):
    out = ['1. 谁调用它，在什么状态下调用：']
    if not c['callers']:
        out.append('   （没有找到直接调用）')
    for r in c['callers']:
        if not r['caller']:
            out.append(f'   - {r["site"]}（未能确定所在函数）')
            continue
        st = [('调用时处于关中断区间' if r['irq_off'] else '调用时不在关中断区间内')]
        st.append('此前已获取未释放：' + '、'.join(r['held']) if r['held'] else '此前无未释放的锁类调用')
        up = '、'.join(u['name'] + (f'[{",".join(u["marks"])}]' if u['marks'] else '') for u in r['up']) or '（未找到）'
        out.append(f'   - {r["site"]} 在 `{r["caller"]}`' + (f'[{",".join(r["marks"])}]' if r['marks'] else '') +
                   f' 中；{"；".join(st)}；路径条件：{r["cond"] or "未取到"}；再上一层调用者：{up}')
    if c['call_sites'] > len(c['callers']):
        out.append(f'   （另有{c["call_sites"] - len(c["callers"])}处调用省略）')
    out.append('2. 作为函数指针登记：')
    out += [f'   - {p}' for p in c['pointers']] or ['   （没有）']
    if c['pointer_sites'] > len(c['pointers']):
        out.append(f'   （另有{c["pointer_sites"] - len(c["pointers"])}处省略）')
    out.append('3. 钩子本身的说明：')
    out.append(f'   {c["hook_doc"]["where"]}\n{c["hook_doc"]["text"]}' if c['hook_doc'] else '   （没有找到）')
    out.append('4. 所调用接口的说明（kernel-doc）：')
    for d in c['api_docs']:
        out.append(f'   - `{d["name"]}`（{d["where"]}）\n{d["text"]}')
    if not c['api_docs']:
        out.append('   （没有找到）')
    if c['api_docs_found'] > len(c['api_docs']):
        out.append(f'   （另有{c["api_docs_found"] - len(c["api_docs"])}个接口的说明省略）')
    return '\n'.join(out)


ASK_OLD = '若参照实现多出来的部分只与那个架构自己的硬件或功能有关，回答no。\n'
ASK_NEW = ASK_OLD + '请结合下面列出的上下文判断：这个函数在被调用的状态下，是否违反了调用者的状态（如关中断、持锁、早期启动）或所调用接口的约定。\n'
TAIL = '\n最后输出一个JSON对象（不要有其他JSON）：'


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    cases = [c for c in json.loads((DEV / 'cases.json').read_text(encoding='utf-8'))['cases'] if c['target']]
    index = {x['case']: x for x in json.loads((DEV / 'prompt_index.json').read_text(encoding='utf-8'))
             if x['variant'] == 'V0'}
    with ThreadPoolExecutor(max_workers=8) as pool:
        ctx = list(pool.map(context, cases))
    out = []
    for c, x in zip(cases, ctx):
        v0 = (V0_CALLS / f'V0_{c["id"]}' / 'prompt.md').read_text(encoding='utf-8')
        assert v0.count(ASK_OLD) == 1 and v0.count(TAIL) == 1, c['id']
        text = v0.replace(ASK_OLD, ASK_NEW).replace(TAIL, '\n【上下文事实（程序列出）】\n' + render(x) + '\n' + TAIL)
        d = CALLS / f'V2_{c["id"]}'
        d.mkdir(parents=True)
        (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
        out.append({'dir': d.name, 'variant': 'V2', 'case': c['id'], 'role': c['role'],
                    'range': index[c['id']]['range']})
    (HERE / 'context.json').write_text(json.dumps(ctx, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'prompt_index.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(out), 'prompts; with callers', sum(bool(x['callers']) for x in ctx), 'with pointers',
          sum(bool(x['pointers']) for x in ctx), 'with hook doc', sum(bool(x['hook_doc']) for x in ctx),
          'with api docs', sum(bool(x['api_docs']) for x in ctx))


if __name__ == '__main__':
    main()
