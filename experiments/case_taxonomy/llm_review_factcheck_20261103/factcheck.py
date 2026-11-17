"""Check the code-fact claims of a model answer against the snapshot (criteria.md section 2). WSL (git).
check(claim, rev) -> (status, detail) with status 'ok', 'mismatch' or 'unverifiable'; detail is a Chinese sentence
stating what the code actually shows (used as feedback in step 2).
"""
from functools import lru_cache
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(HERE.parents[2]))
import checker as CK  # noqa: E402
from linux_bug_analyze.path_conditions import analyze  # noqa: E402


@lru_cache(maxsize=None)
def function(rev, path, name):
    for s, e, n, t in CK.functions(rev, path):
        if n == name:
            return t
    return None


def truth(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ('true', 'false', 'yes', 'no'):
        return v.strip().lower() in ('true', 'yes')
    return None


def norm(s):
    return re.sub(r'\s+', '', str(s))


def cond_text(conds):
    out = []
    for t, pos in conds:
        out.append(norm(t) if pos else '!(' + norm(t) + ')')
    return '&&'.join(out)


def check(claim, rev):
    if not isinstance(claim, dict):
        return 'unverifiable', '格式不对'
    kind, path, fn = claim.get('type'), claim.get('file'), claim.get('function')
    if not (isinstance(path, str) and isinstance(fn, str)):
        return 'unverifiable', '缺少file或function'
    text = function(rev, path.strip(), fn.strip())
    if text is None:
        return 'unverifiable', f'在{path}中找不到函数{fn}'
    head = text.split('{', 1)[0]
    names = [c.name for c in analyze(text)]
    if kind == 'annotation':
        ann, want = str(claim.get('annotation', '')).strip(), truth(claim.get('present'))
        if not ann or want is None:
            return 'unverifiable', '缺少annotation或present'
        actual = re.search(r'(^|\W)' + re.escape(ann) + r'(\W|$)', head) is not None
        sig = ' '.join(head.split())
        return ('ok' if actual == want else 'mismatch',
                f'代码中{fn}的签名是“{sig}”，{"含" if actual else "不含"}{ann}')
    if kind == 'calls':
        callee, want = str(claim.get('callee', '')).strip(), truth(claim.get('present'))
        if not callee or want is None:
            return 'unverifiable', '缺少callee或present'
        actual = callee in names
        return ('ok' if actual == want else 'mismatch', f'代码中{fn}{"调用了" if actual else "没有调用"}{callee}')
    if kind == 'order':
        first, then = str(claim.get('first', '')).strip(), str(claim.get('then', '')).strip()
        if not first or not then:
            return 'unverifiable', '缺少first或then'
        fi = [i for i, n in enumerate(names) if n == first]
        ti = [i for i, n in enumerate(names) if n == then]
        if not fi or not ti:
            miss = '、'.join(x for x, l in ((first, fi), (then, ti)) if not l)
            return 'mismatch', f'代码中{fn}没有调用{miss}'
        ok = min(fi) < max(ti)
        seq = ' → '.join(n for n in names if n in (first, then))
        return ('ok' if ok else 'mismatch', f'代码中{fn}里这两个调用的出现顺序是：{seq}')
    if kind == 'condition':
        callee, cond = str(claim.get('callee', '')).strip(), norm(claim.get('condition', ''))
        if not callee or not cond:
            return 'unverifiable', '缺少callee或condition'
        occ = [c for c in analyze(text) if c.name == callee]
        if not occ:
            return 'mismatch', f'代码中{fn}没有调用{callee}'
        neg, core = cond.startswith('!'), cond.lstrip('!')
        while core.startswith('(') and core.endswith(')'):
            core = core[1:-1]
        # the claimed condition matches one enclosing condition with the same text and the same polarity
        texts = [cond_text(c.conds) for c in occ]
        ok = all(any(core and (core in norm(t) or norm(t) in core) and pos != neg for t, pos in c.conds) for c in occ)
        shown = '；'.join(f'第{k + 1}处：{t or "无条件"}' for k, t in enumerate(texts))
        return ('ok' if ok else 'mismatch', f'代码中{fn}里{callee}各处调用所在的条件为：{shown}')
    return 'unverifiable', f'类型{kind}不在可核对的范围内'
