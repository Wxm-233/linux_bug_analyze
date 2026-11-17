"""Program facts of development round 2 (criteria.md section 1): the round-1 facts of
llm_review_v2_dev_20261104/facts.py (imported, unchanged) plus, for CTX flags, the call sites of the flagged function
in the architecture directory, and for R10 flags, the common-code functions that call both the flagged function and a
missing callee, with line numbers and order. WSL (git); no model."""
from pathlib import Path
import ast
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'llm_review_v2_dev_20261104'))
import facts as F1  # noqa: E402
from facts import ARCH_TABLE, ARCH_NAME, analyze, CK, git  # noqa: E402,F401


def enclosing(rev, path, line):
    for s, e, n, t in CK.functions(rev, path):
        if s <= line <= e:
            return s, n, t
    return None


def co_callers(rev, name, callee, limit=2):
    """Common-code functions that call both name and callee: [(path, func, line of name, line of callee)]."""
    out, seen = [], set()
    hits = git('grep', '-n', '-E', r'(^|[^A-Za-z0-9_])' + name + r'[[:space:]]*\(', rev, '--',
               *[f'{d}/*.c' for d in F1.COMMON])
    for h in hits.splitlines():
        p = h.split(':', 3)  # rev:path:line:text
        if len(p) < 4 or not p[2].isdigit():
            continue
        path = p[1]
        enc = enclosing(rev, path, int(p[2]))
        if not enc or (path, enc[1]) in seen or enc[1] == name:
            continue
        seen.add((path, enc[1]))
        s, fn, text = enc
        calls = analyze(text)
        a = [s + c.line - 1 for c in calls if c.name == name]
        b = [s + c.line - 1 for c in calls if c.name == callee]
        if a and b:
            out.append((path, fn, a[0], b[0]))
        if len(out) >= limit:
            break
    return out


def facts(row, arch):
    fs = F1.facts(row, arch)
    texts = []
    an = ARCH_NAME[arch]
    rev, rule, name = row['snapshot'], row['rule'], row['name']
    if rule == 'CTX':
        sites = F1.call_sites(rev, name, (f'arch/{arch}',), 5)
        texts.append(f'{name}在{an}目录中的调用位置：' + ('；'.join(sites) if sites else '没有找到') + '。')
    elif rule == 'R10':
        m = re.search(r'call (\[.*\]),', row.get('reason') or '')
        for x in (ast.literal_eval(m.group(1)) if m else [])[:4]:
            both = co_callers(rev, name, x)
            if both:
                texts.append('；'.join(f'{p}的{fn}中，第{a}行调用{name}，第{b}行调用{x}（{name}在{"前" if a < b else "后"}）'
                                      for p, fn, a, b in both) + '。')
            else:
                texts.append(f'公共代码（init、kernel、mm）中没有同时调用{name}和{x}的函数。')
    return fs + [{'id': f'F{len(fs) + k + 1}', 'text': t} for k, t in enumerate(texts)]
