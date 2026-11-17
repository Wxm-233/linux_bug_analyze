"""Judgment benchmark (criteria.md sections 1-4): positives (dev set, at fix^), program-paired reference
implementations, negatives, V1 evidence and the V0/V1 prompts. WSL; no model calls; labels are read only to pick
the positives' target functions. Output: cases.json and <CALLS>/<V0|V1>_<P|N>_<id>/prompt.md, prompt_index.json.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
import modules as M  # noqa: E402
from modules import CK, analyze, call_names, function  # noqa: E402
from linux_bug_analyze.path_conditions import strip_code  # noqa: E402

sys.path.insert(0, str(HERE.parent / 'cross_arch_sample_set_20261102'))
from collect import TRAILER  # noqa: E402

CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_dev_20261103'
LABELS = HERE.parent / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
END = CK.END
REF = ('arm64', 'x86', 'loongarch')
SEED, N_NEG = 20261106, 50
CONST = re.compile(r'^[A-Z][A-Z0-9_]{2,}$')
IDENT = re.compile(r'[A-Za-z_]\w*')


def git(*a):
    return M.git(*a)


def message(sha, limit=15):
    lines = git('log', '-1', '--format=%B', sha).splitlines()
    body = [l for l in lines if not TRAILER.match(l.strip())]
    return '\n'.join(body[:limit]).strip()


def numbered(f, limit):
    lines = f['text'].splitlines()
    more = len(lines) - limit if len(lines) > limit else 0
    out = '\n'.join(f'{f["start"] + k:5d}  {l}' for k, l in enumerate(lines[:limit]))
    return out + (f'\n...（其余{more}行省略）' if more else '')


# ------------------------------------------------------------------ positives
def old_lines(sha, path):
    """Old-side line numbers that the fix removes or inserts next to."""
    out = set()
    for m in re.finditer(r'^@@ -(\d+)(?:,(\d+))? ', git('show', '--format=', '-U0', sha, '--', path), re.M):
        s, n = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        out |= set(range(s, s + n)) if n else {s, s + 1}
    return out


def target(r):
    rev = r['commit'] + '^'
    best = None
    for f in r['functions']:
        path, name = f.rsplit(':', 1)
        if not path.startswith('arch/riscv/'):
            continue
        fn = function(rev, path, name)
        if not fn:
            continue
        ov = len(old_lines(r['commit'], path) & set(range(fn['start'], fn['end'] + 1)))
        if best is None or ov > best[0]:
            best = (ov, fn)
    return best[1] if best else None


# ------------------------------------------------------------------ pairing (section 2)
def callset(f):
    return call_names(f['text'])


def defs_same_name(rev, name):
    found = M.defs_in(rev, [name], [f'arch/{a}/*.c' for a in REF] + [f'arch/{a}/*.h' for a in REF])
    out = {}
    for p in sorted(found.get(name, []), key=lambda p: not p.endswith('.c')):
        a = p.split('/')[1]
        if a in REF and a not in out:
            f = function(rev, p, name)
            if f:
                out[a] = f
    return out


def best_similar(rev, rv_calls, paths):
    best = None
    for p in paths:
        for s, e, n, t in M.funcs(rev, p):
            cs = call_names(t)
            inter = len(cs & rv_calls)
            if inter < 2:
                continue
            j = inter / len(cs | rv_calls)
            if j >= 0.25 and (best is None or j > best[0]):
                best = (j, {'path': p, 'name': n, 'start': s, 'end': e, 'text': t})
    return best


def pair(rev, fn):
    """[(arch, how, score, ref function)] with at most two arches (criteria section 2)."""
    same = defs_same_name(rev, fn['name'])
    out = [(a, 'same_name', 1.0, f) for a, f in same.items()]
    rel = fn['path'].split('/', 2)[2]
    top = rel.split('/')[0]
    rv_calls = callset(fn)
    for a in REF:
        if a in same:
            continue
        sub = f'arch/{a}/{rel}'
        if sub in M.files(rev, f'arch/{a}', ('.c',)):
            b = best_similar(rev, rv_calls, [sub])
            if b:
                out.append((a, 'same_subpath', b[0], b[1]))
                continue
        b = best_similar(rev, rv_calls, M.files(rev, f'arch/{a}/{top}', ('.c',)))
        if b:
            out.append((a, 'same_top_dir', b[0], b[1]))
    out.sort(key=lambda x: (x[1] != 'same_name', -x[2], REF.index(x[0])))
    return out[:2]


# ------------------------------------------------------------------ V1 evidence (section 4)
def first_line(f, word):
    for k, l in enumerate(f['text'].splitlines()):
        if re.search(r'(^|[^A-Za-z0-9_])' + re.escape(word) + r'([^A-Za-z0-9_]|$)', l):
            return f['start'] + k
    return None


def blame(rev, path, line):
    out = git('blame', '--porcelain', '-L', f'{line},{line}', rev, '--', path)
    m = re.match(r'([0-9a-f]{40}) ', out)
    return m.group(1)[:12] if m else None


def evidence(rev, fn, refs):
    rv_calls = callset(fn)
    rv_ids = set(IDENT.findall(strip_code(fn['text'])))
    ref_only, conds = {}, {}
    for a, _, _, f in refs:
        for c in analyze(f['text']):
            if c.name not in rv_calls:
                ref_only.setdefault(c.name, set()).add(a)
                if (c.name, a) not in conds:
                    conds[(c.name, a)] = ' 且 '.join(e if pos else f'非({e})' for e, pos in c.conds) or '无条件'
    calls = sorted(ref_only, key=lambda c: (-len(ref_only[c]), c))
    const_arch = {}
    for a, _, _, f in refs:
        for x in set(IDENT.findall(strip_code(f['text']))):
            if CONST.match(x) and x not in rv_ids:
                const_arch.setdefault(x, set()).add(a)
    consts = sorted(const_arch, key=lambda c: (-len(const_arch[c]), c))
    rv_only = sorted(rv_calls - set().union(*(callset(f) for _, _, _, f in refs))) if refs else []
    picked = [('call', c) for c in calls[:8]] + [('const', c) for c in consts[:4]] + [('rv', c) for c in rv_only[:3]]
    rest = [('call', c) for c in calls[8:]] + [('const', c) for c in consts[4:]] + [('rv', c) for c in rv_only[3:]]
    picked += rest[:15 - len(picked)]
    order = {'call': 0, 'const': 1, 'rv': 2}
    picked.sort(key=lambda x: order[x[0]])
    diffs, reasons, seen = [], [], set()
    for k, (kind, x) in enumerate(picked, 1):
        if kind == 'rv':
            diffs.append(f'D{k} RISC-V调用了`{x}`，参照实现中没有')
            continue
        arches = sorted(ref_only[x] if kind == 'call' else const_arch[x])
        cond = '；'.join(f'{a}中的条件：{conds[(x, a)]}' for a in arches if (x, a) in conds)
        what = '调用' if kind == 'call' else '使用常量或宏'
        diffs.append(f'D{k} {"、".join(arches)}{what}`{x}`，RISC-V没有' + (f'（{cond}）' if cond else ''))
        if len([d for d in diffs if 'RISC-V没有' in d]) <= 6:
            for a, _, _, f in refs:
                if a not in arches:
                    continue
                ln = first_line(f, x)
                sha = ln and blame(rev, f['path'], ln)
                if sha and sha not in seen:
                    seen.add(sha)
                    reasons.append(f'--- D{k}：{f["path"]}第{ln}行由提交{sha}引入\n{message(sha)}')
                break
    d = fn['path'].rsplit('/', 1)[0]
    base = fn['path'].rsplit('/', 1)[1][:-2]
    mk = [l.strip() for l in git('show', f'{rev}:{d}/Makefile').splitlines() if re.search(r'\b' + base + r'\.o\b', l)]
    callers = []
    for l in git('grep', '-n', '-w', fn['name'], rev, '--', 'arch/riscv').splitlines():
        parts = l.split(':', 3)
        if len(parts) == 4 and not (parts[1] == fn['path'] and fn['start'] - 8 <= int(parts[2]) <= fn['end']):
            callers.append(f'{parts[1]}:{parts[2]}: {parts[3].strip()}')
    return {'diffs': diffs, 'reasons': reasons, 'makefile': mk[:3], 'callers': callers[:6]}


# ------------------------------------------------------------------ negatives (section 3)
def fixed_later(rev, path, s, e):
    out = git('log', '--format=%H', '-s', '-L', f'{s},{e}:{path}', f'{rev}..{END}')
    for sha in re.findall(r'^[0-9a-f]{40}$', out, re.M):
        if re.search(r'^\s*Fixes:', git('log', '-1', '--format=%B', sha), re.M | re.I):
            return True
    return False


def negatives_for(r, fn, targets, rnd):
    rev = r['commit'] + '^'
    top = '/'.join(fn['path'].split('/')[:3])
    cands = []
    for p in M.files(rev, top, ('.c',)):
        for s, e, n, t in M.funcs(rev, p):
            if e - s + 1 >= 5 and (p, n) not in targets:
                cands.append({'path': p, 'name': n, 'start': s, 'end': e, 'text': t})
    rnd.shuffle(cands)
    out = []
    for c in cands:
        refs = pair(rev, c)
        if not refs:
            continue
        rv_calls = callset(c)
        if not any(callset(f) - rv_calls for _, _, _, f in refs):
            continue
        if fixed_later(rev, c['path'], c['start'], c['end']):
            continue
        out.append((c, refs))
        if len(out) == 2:
            break
    return out


# ------------------------------------------------------------------ prompts (section 4)
HEAD = ('你是Linux内核跨架构问题的分析助手。以下材料取自内核某一版本。只根据材料和你对内核的了解判断，拿不准就回答'
        'unsure。\n\n')


def code_blocks(fn, refs):
    out = [f'【RISC-V：{fn["path"]}，函数`{fn["name"]}`】\n{numbered(fn, 150)}']
    for a, how, _, f in refs:
        out.append(f'【参照 {a}：{f["path"]}，函数`{f["name"]}`】\n{numbered(f, 100)}')
    if not refs:
        out.append('【参照】程序没有找到其他架构中对应的实现。')
    return '\n\n'.join(out)


def v0(fn, refs):
    return HEAD + f'''下面是RISC-V中的一个函数，以及程序在其他架构中找到的对应实现。

请回答：参照实现中，有没有RISC-V同样应满足、而RISC-V的这个函数没有做到的要求？若有，说明是什么，并引用RISC-V函数中的行号；若参照实现多出来的部分只与那个架构自己的硬件或功能有关，回答no。

{code_blocks(fn, refs)}

最后输出一个JSON对象（不要有其他JSON）：
{{"verdict": "yes|no|unsure", "problem": "一句话或空", "lines": [行号], "why": "一句话"}}
'''


def v1(fn, refs, ev):
    facts = '\n'.join([f'编译这个文件的Makefile行：{"；".join(ev["makefile"]) or "（未找到）"}',
                       'RISC-V中调用这个函数的位置：', *(ev['callers'] or ['（没有找到）'])])
    return HEAD + f'''下面是RISC-V中的一个函数，以及程序在其他架构中找到的对应实现。程序列出了两边的差异，以及参照中这些差异是由哪个提交、出于什么理由引入的。

请逐条判断每个差异：
1. 参照这样写的理由，在RISC-V上是否同样成立（reason_applies）？
2. RISC-V是否已经有相应的处理（riscv_handles）？可能在本函数中，也可能在调用者或别处。
回答“理由不成立”（reason_applies为no）或“已有处理”（riscv_handles为yes）时，必须在evidence中引用RISC-V的具体行号、函数或配置；没有引用的，按unsure处理。
差异中如有无关的（例如只是写法不同），reason_applies回答no，并说明原因。

最后给出整体分数score：
- 3：确定RISC-V缺少某项必要的处理，或有错误；
- 2：很可能缺少；
- 1：有疑点，但证据不足；
- 0：没有问题。
并给出问题描述，以及RISC-V函数中的行号（缺失时引用应当加处理的位置附近的行）。

{code_blocks(fn, refs)}

【逐条差异（程序列出）】
{chr(10).join(ev['diffs']) or '（没有列出差异）'}

【差异的来历（参照中引入这些行的提交）】
{chr(10).join(ev['reasons']) or '（无）'}

【RISC-V事实（程序列出）】
{facts}

最后输出一个JSON对象（不要有其他JSON）：
{{"items": [{{"id": "D1", "reason_applies": "yes|no|unsure", "riscv_handles": "yes|no|unsure", "evidence": "引用", "why": "一句话"}}], "score": 0, "problem": "一句话或空", "lines": [行号]}}
'''


def main():
    if CALLS.exists():
        raise SystemExit('preserve')
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    pos = [r for r in labels if r['dev'] and r['cross'] == 'C' and r['flag'] not in ('无关', '构建错误')]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tg = list(pool.map(target, pos))
    targets = {(f['path'], f['name']) for f in tg if f}
    with ThreadPoolExecutor(max_workers=8) as pool:
        prefs = list(pool.map(lambda x: pair(x[0]['commit'] + '^', x[1]) if x[1] else [], zip(pos, tg)))
    rnd = random.Random(SEED)
    neg = []
    for r, fn in zip(pos, tg):
        if fn:
            neg += [(r, c, refs) for c, refs in negatives_for(r, fn, targets, rnd)]
    found = len(neg)
    if len(neg) > N_NEG:
        neg = random.Random(SEED).sample(neg, N_NEG)
    cases = []
    for r, fn, refs in zip(pos, tg, prefs):
        cases.append({'id': f'P_{r["id"]}', 'role': 'pos', 'label_id': r['id'], 'rev': r['commit'] + '^', 'fn': fn,
                      'refs': refs, 'label_counterpart': r['counterpart']})
    for k, (r, c, refs) in enumerate(neg):
        cases.append({'id': f'N_{k:03d}', 'role': 'neg', 'label_id': r['id'], 'rev': r['commit'] + '^', 'fn': c,
                      'refs': refs})
    with ThreadPoolExecutor(max_workers=8) as pool:
        evs = list(pool.map(lambda c: evidence(c['rev'], c['fn'], c['refs']) if c['fn'] else None, cases))
    index, record = [], []
    for c, ev in zip(cases, evs):
        fn, refs = c['fn'], c['refs']
        rec = {'id': c['id'], 'role': c['role'], 'label_id': c['label_id'], 'rev': c['rev'],
               'target': fn and {k: fn[k] for k in ('path', 'name', 'start', 'end')},
               'refs': [{'arch': a, 'how': how, 'score': round(s, 3), 'path': f['path'], 'name': f['name']}
                        for a, how, s, f in refs],
               'label_counterpart': c.get('label_counterpart'), 'evidence': ev}
        record.append(rec)
        if not fn:
            continue
        for var, text in (('V0', v0(fn, refs)), ('V1', v1(fn, refs, ev))):
            d = CALLS / f'{var}_{c["id"]}'
            d.mkdir(parents=True)
            (d / 'prompt.md').write_text(text, encoding='utf-8', newline='\n')
            index.append({'dir': d.name, 'variant': var, 'case': c['id'], 'role': c['role'],
                          'range': [fn['start'], fn['end']]})
    (HERE / 'cases.json').write_text(json.dumps({'negatives_found': found, 'cases': record}, indent=1,
                                                ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'prompt_index.json').write_text(json.dumps(index, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print('positives', len(pos), 'built', sum(1 for f in tg if f), 'with refs', sum(1 for p in prefs if p),
          'negatives found', found, 'used', len(neg), 'prompts', len(index))


if __name__ == '__main__':
    main()
