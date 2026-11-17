"""Steps 2b and 2c of criteria_amendment1.md: find RISC-V candidate functions for a reference commit by contract
(same hook, same common caller, identifier fallback) on the last version before the reference, and list structured
facts for each candidate with the path-condition library. No model calls.
"""
from collections import Counter
from functools import lru_cache
import re
import sys

from common import CK, ROOT, git

sys.path.insert(0, str(ROOT.parent.parent))
from linux_bug_analyze.path_conditions import analyze  # noqa: E402

MAX_FUNCS, MAX_LINES, MAX_HIT_LINES, MAX_CALLERS, TOP_IDENTS, MAX_IDENT_FILES = 6, 400, 30, 5, 15, 20
GENERIC = {'init', 'setup', 'main', 'probe', 'remove', 'show', 'store', 'open', 'release', 'read', 'write', 'ioctl'}
KEYWORDS = set('''auto break case char const continue default do double else enum extern float for goto if inline int
long register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while
bool true false NULL likely unlikely return void u8 u16 u32 u64 s8 s16 s32 s64 size_t ssize_t unsigned long int char
__init __user __iomem __always_inline noinline static_branch_likely READ_ONCE WRITE_ONCE IS_ENABLED CONFIG
include define ifdef ifndef endif else elif undef pr_err pr_warn pr_info pr_debug WARN_ON BUG_ON EXPORT_SYMBOL
EXPORT_SYMBOL_GPL'''.split())
DISABLE = re.compile(r'(raw_)?local_irq_(disable|save)$')
ENABLE = re.compile(r'(raw_)?local_irq_(enable|restore)$')
REF_PREFIXES = ('arch/arm64/', 'arch/x86/', 'arch/loongarch/')


def ref_rev(sha):
    date = git('log', '-1', '--format=%cI', sha).strip()
    return git('rev-list', '-1', f'--before={date}', 'df2908090cda').strip()


def ref_changes(sha):
    """Changed (path, function) pairs on the parent for the other-arch and common files, and the changed lines."""
    files = [f for f in git('show', '--no-renames', '--name-only', '--format=', sha).split()
             if f.endswith(('.c', '.h')) and (f.startswith(REF_PREFIXES) or not f.startswith(('arch/', 'tools/',
                                                                                              'Documentation/')))]
    funcs, lines = [], []
    for f in files:
        diff = git('diff', '-U0', sha + '^', sha, '--', f)
        lines += [l[1:] for l in diff.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---'))]
        spans = CK.functions(sha + '^', f)
        for m in re.finditer(r'^@@ -(\d+)(?:,(\d+))? ', diff, re.M):
            s0, n = int(m.group(1)), int(m.group(2) or 1)
            for s, e, name, _ in spans:
                if s <= s0 + max(n, 1) - 1 and s0 <= e and (f, name) not in funcs:
                    funcs.append((f, name))
    return funcs, lines


def definitions(rev, names, where=('arch/riscv/*.c', 'arch/riscv/*.h')):
    """{name: [path]} for functions defined under `where` at rev (one git grep for all names)."""
    names = sorted({n for n in names if re.fullmatch(r'[A-Za-z_]\w*', n)})
    out = {}
    for k in range(0, len(names), 60):
        chunk = names[k:k + 60]
        pat = r'^[A-Za-z_].*[^A-Za-z0-9_](' + '|'.join(chunk) + r')\s*\('
        for line in git('grep', '-n', '-E', pat, rev, '--', *where).splitlines():
            parts = line.split(':', 3)
            if len(parts) < 4:
                continue
            path = parts[1]
            for n in chunk:
                if re.search(r'[^A-Za-z0-9_]' + n + r'\s*\(', ' ' + parts[3]):
                    out.setdefault(n, set()).add(path)
    return {n: sorted(p) for n, p in out.items()}


@lru_cache(maxsize=None)
def funcs_at(rev, path):
    return CK.functions(rev, path)


def function(rev, path, name):
    for s, e, n, t in funcs_at(rev, path):
        if n == name:
            return s, e, t
    return None


def callers(rev, name):
    out = git('grep', '-n', '-E', r'(^|[^A-Za-z0-9_])' + re.escape(name) + r'[[:space:]]*\(', rev, '--', '*.c',
              ':(exclude)arch',
              ':(exclude)tools', ':(exclude)Documentation')
    found = []
    for line in out.splitlines():
        parts = line.split(':', 3)
        if len(parts) < 4:
            continue
        path, ln = parts[1], int(parts[2])
        for s, e, n, _ in funcs_at(rev, path):
            if s <= ln <= e and n != name and (path, n) not in found:
                found.append((path, n))
        if len(found) >= MAX_CALLERS:
            break
    return found


def identifiers(lines, names):
    cnt = Counter(t for l in lines for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]{3,}', l) if t not in KEYWORDS)
    for n in names:
        cnt[n] += 5
    return [t for t, _ in cnt.most_common(TOP_IDENTS)]


def candidates(sha, hooks=()):
    rev = ref_rev(sha)
    changed, lines = ref_changes(sha)
    names = [n for _, n in changed] + [h for h in hooks if isinstance(h, str)]
    names = [n for n in dict.fromkeys(names) if n not in GENERIC and not n.endswith('__init')]
    cands = []  # (route, path, name)

    def add(route, path, name):
        if (path, name) not in [(p, n) for _, p, n in cands]:
            cands.append((route, path, name))

    for n, paths in definitions(rev, names).items():
        for p in paths:
            add(1, p, n)
    called = []
    for n in names:
        for path, caller in callers(rev, n):
            f = function(rev, path, caller)
            if f:
                called += [c.name for c in analyze(f[2])]
    for n, paths in definitions(rev, called).items():
        for p in paths:
            add(2, p, n)
    idents = [i for i in identifiers(lines, names)
              if len(git('grep', '-l', '-w', i, rev, '--', 'arch/riscv').splitlines()) <= MAX_IDENT_FILES]
    hits = []
    if idents:
        args = [x for i in idents for x in ('-e', i)]
        out = git('grep', '-n', '-w', *args, rev, '--', 'arch/riscv/*.c', 'arch/riscv/*.h', 'arch/riscv/*.S')
        for line in out.splitlines():
            parts = line.split(':', 3)
            if len(parts) < 4:
                continue
            path, ln = parts[1], int(parts[2])
            hits.append(f'{path}:{ln}: {parts[3].strip()[:120]}')
            if path.endswith(('.c', '.h')):
                for s, e, n, _ in funcs_at(rev, path):
                    if s <= ln <= e:
                        add(3, path, n)
    picked, total = [], 0
    for route, path, name in cands:
        f = function(rev, path, name)
        if not f:
            continue
        s, e, text = f
        size = text.count('\n') + 1
        if total + size > MAX_LINES:
            continue
        picked.append({'route': route, 'path': path, 'name': name, 'start': s, 'end': e, 'text': text})
        total += size
        if len(picked) >= MAX_FUNCS:
            break
    return {'rev': rev[:12], 'ref_functions': [f'{p}:{n}' for p, n in changed], 'identifiers': idents,
            'all_candidates': [{'route': r, 'path': p, 'name': n} for r, p, n in cands],
            'picked': picked, 'hit_lines': hits[:MAX_HIT_LINES]}


def facts(cand):
    """Step 2c: calls with path conditions, and calls inside irq-disabled regions."""
    calls = analyze(cand['text'])
    rows = []
    for c in calls[:40]:
        cond = ' 且 '.join(e if pos else f'非({e})' for e, pos in c.conds) if c.conds else '（无条件）'
        rows.append(f'第{cand["start"] + c.line - 1}行 调用 {c.name}，条件：{cond}')
    irq, k = [], 0
    while k < len(calls):
        if DISABLE.fullmatch(calls[k].name):
            j = k + 1
            while j < len(calls) and not ENABLE.fullmatch(calls[j].name):
                j += 1
            irq += [f'第{cand["start"] + c.line - 1}行 {c.name}' for c in calls[k + 1:j]]
            k = j
        k += 1
    return rows, irq
