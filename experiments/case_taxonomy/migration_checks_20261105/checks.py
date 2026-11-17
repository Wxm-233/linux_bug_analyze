"""Program-executed migration checks (criteria.md sections 1 and 2) on one patched commit.

    check(base, head, arch, refs, ref_arch) -> {'flags': [...], 'facts': [...]}

C1a build entries for new/renamed sources; C1b call sites still using a changed function's old parameter count;
C1c leftover `old(args)` after the patch replaced it by `new(args)`; C1d reference functions without a counterpart
change (same-name function left untouched, or a __weak override the reference adds but the target lacks);
C2a free calls whose object is allocated by a non-matching allocator; C2b defined functions whose return type or
parameter count differs from the common declaration, or arch_* hooks the common code does not declare; C2c facts
(allocations found by C2a, prototypes of newly called common functions, declarations of newly used members).
WSL (git); no model calls.
"""
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(HERE.parent / 'patch_check_20261105'))
import checker as CK  # noqa: E402
import patch_check as PC  # noqa: E402  (changed_functions)

COMMON = ('include', 'kernel', 'mm', 'lib', 'init', 'net', 'drivers', 'fs', 'block')
FREE = {'kfree': 'k', 'kfree_sensitive': 'k', 'kvfree': 'kv', 'vfree': 'v', 'free_pages': 'p', 'free_page': 'p'}
ALLOC = {'kmalloc': 'k', 'kzalloc': 'k', 'kcalloc': 'k', 'kmalloc_array': 'k', 'krealloc': 'k', 'kmemdup': 'k',
         'kvmalloc': 'kv', 'kvzalloc': 'kv', 'kvcalloc': 'kv', 'kvmalloc_array': 'kv', 'kvrealloc': 'kv',
         'vmalloc': 'v', 'vzalloc': 'v', '__vmalloc': 'v', 'vmalloc_array': 'v', 'vcalloc': 'v',
         '__get_free_pages': 'p', 'get_zeroed_page': 'p'}
KEYWORDS = {'if', 'for', 'while', 'switch', 'return', 'sizeof', 'typeof', 'defined', 'do', '__attribute__'}


def show(rev, path):
    return CK.git('show', f'{rev}:{path}')


def hunks(base, head, *paths):
    """[(file, [(sign, text)])] of base..head, one list per hunk."""
    out, cur, f = [], None, None
    for line in CK.git('diff', '-U0', base, head, '--', *paths).splitlines():
        if line.startswith('+++ '):
            f = line[6:] if line.startswith('+++ b/') else None
        elif line.startswith('@@'):
            cur = []
            out.append((f, cur))
        elif cur is not None and line[:1] in '+-' and not line.startswith(('+++', '---')):
            cur.append((line[0], line[1:]))
    return out


def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    out.append(cur)
    return [a.strip() for a in out if a.strip()]


def call_sites(text, name):
    """[(line, argc)] of name(...) calls in text (definitions included; callers filter)."""
    out = []
    for m in re.finditer(rf'(?<![A-Za-z0-9_]){re.escape(name)}\s*\(', text):
        depth, k = 1, m.end()
        while k < len(text) and depth:
            depth += {'(': 1, ')': -1}.get(text[k], 0)
            k += 1
        args = text[m.end():k - 1]
        tail = text[k:k + 40].lstrip()
        if tail.startswith('{') or tail.startswith(';') and re.search(r'\b(struct|int|void|long|char|unsigned)\b', args):
            continue  # a definition or a prototype
        out.append((text.count('\n', 0, m.start()) + 1, 0 if args.strip() in ('', 'void') else len(split_args(args))))
    return out


def prototypes(text, names):
    """{name: (return_text, argc)} for declarations/definitions in text."""
    out = {}
    for n in names:
        for m in re.finditer(rf'^([A-Za-z_][\w \t\*]*?)\b{re.escape(n)}\s*\(([^;{{]*?)\)\s*[;{{]', text, re.M | re.S):
            ret = re.sub(r'\b(extern|static|inline|__always_inline|__weak|notrace|__init|noinstr|__cold)\b', '', m.group(1))
            ret = re.sub(r'\s+', ' ', ret).strip()
            if not ret or ret in KEYWORDS or ret.endswith(('=', 'return')):
                continue
            args = m.group(2).strip()
            out[n] = (ret, 0 if args in ('', 'void') else len(split_args(args)))
            break
    return out


def arch_files(rev, arch):
    return [f for f in CK.git('ls-tree', '-r', '--name-only', rev, f'arch/{arch}').splitlines()
            if f.endswith(('.c', '.h', '.S'))]


# ------------------------------------------------------------------ C1
def c1a(base, head, arch):
    flags = []
    for line in CK.git('diff', '--name-status', '-M', base, head, '--', f'arch/{arch}').splitlines():
        parts = line.split('\t')
        status, new = parts[0], parts[-1]
        old = parts[1] if status.startswith('R') else None
        if not (status.startswith(('A', 'R')) and new.endswith(('.c', '.S'))):
            continue
        folder = new.rsplit('/', 1)[0]
        mk = show(head, f'{folder}/Makefile')
        stem = new.rsplit('/', 1)[1].rsplit('.', 1)[0]
        if not re.search(rf'\b{re.escape(stem)}\.o\b', mk):
            flags.append({'check': 'C1a', 'where': f'{folder}/Makefile',
                          'what': f'新增的{new}没有在Makefile中加入{stem}.o'})
        if old:
            ostem = old.rsplit('/', 1)[1].rsplit('.', 1)[0]
            if re.search(rf'\b{re.escape(ostem)}\.o\b', show(head, f'{old.rsplit("/", 1)[0]}/Makefile')):
                flags.append({'check': 'C1a', 'where': f'{old.rsplit("/", 1)[0]}/Makefile',
                              'what': f'{old}已改名为{new}，Makefile中仍引用{ostem}.o'})
    return flags


def c1b(base, head, arch):
    flags = []
    files = [f for f in CK.git('diff', '--name-only', base, head).split() if f.endswith(('.c', '.h'))]
    names = {n for _, n in PC.changed_functions(base, head)}
    for f in files:
        names |= set(re.findall(r'^[+-][^\n]*?\b([A-Za-z_]\w*)\s*\([^;]*\)\s*;', '\n'.join(
            l for l in CK.git('diff', '-U0', base, head, '--', f).splitlines()), re.M))
    before, after = {}, {}
    for f in files:
        before.update({k: v for k, v in prototypes(show(base, f), names).items() if k not in before})
        after.update({k: v for k, v in prototypes(show(head, f), names).items() if k not in after})
    for n in sorted(set(before) & set(after)):
        old, new = before[n][1], after[n][1]
        if old == new:
            continue
        for p in CK.git('grep', '-l', '-w', n, head, '--', f'arch/{arch}').split():
            path = p.split(':', 1)[1]
            for line, argc in call_sites(show(head, path), n):
                if argc == old and argc != new:
                    flags.append({'check': 'C1b', 'where': f'{path}:{line}',
                                  'what': f'{n}的参数个数由{old}改为{new}，此处仍按{old}个参数调用'})
    return flags


def c1c(base, head, arch):
    flags, seen = [], set()
    for f, h in hunks(base, head, f'arch/{arch}'):
        minus = [t for s, t in h if s == '-']
        plus = [t for s, t in h if s == '+']
        for a, b in zip(minus, plus):
            ca = dict((args.strip(), n) for n, args in re.findall(r'\b([A-Za-z_]\w*)\s*\(([^()]*)\)', a))
            for n2, args in re.findall(r'\b([A-Za-z_]\w*)\s*\(([^()]*)\)', b):
                n1 = ca.get(args.strip())
                if n1 and n1 != n2 and n1 not in KEYWORDS and args.strip() and (n1, args.strip()) not in seen:
                    seen.add((n1, args.strip()))
                    needle = f'{n1}({args.strip()})'
                    for hit in CK.git('grep', '-n', '-F', needle, head, '--', f'arch/{arch}').splitlines()[:5]:
                        _, path, line, _ = hit.split(':', 3)
                        flags.append({'check': 'C1c', 'where': f'{path}:{line}',
                                      'what': f'补丁把{needle}改成了{n2}(…)，此处仍是{needle}'})
    return flags


def ref_functions(refs, ref_arch):
    names = set()
    for c in refs:
        names |= {n for p, n in PC.changed_functions(c + '^', c) if p.startswith(f'arch/{ref_arch}/')
                  or ref_arch == 'common'}
    return names


def c1d(base, head, arch, refs, ref_arch):
    if ref_arch == 'common':
        return []
    flags = []
    touched = {n for _, n in PC.changed_functions(base, head)}
    for n in sorted(ref_functions(refs, ref_arch)):
        defined = []
        for p in CK.git('grep', '-l', '-w', n, base, '--', f'arch/{arch}').split():
            path = p.split(':', 1)[1]
            if path.endswith(('.c', '.h')) and any(x == n for _, _, x, _ in CK.functions(base, path)):
                defined.append(path)
        if defined and n not in touched:
            flags.append({'check': 'C1d', 'where': f'{defined[0]}:{n}',
                          'what': f'参照补丁改动了{n}，目标架构有同名函数，补丁没有改动它'})
        elif not defined and n not in touched and \
                CK.git('grep', '-l', '-E', rf'__weak.*\b{n}\s*\(', base, '--', *COMMON).strip():
            flags.append({'check': 'C1d', 'where': n,
                          'what': f'参照补丁定义了覆盖公共__weak默认实现的{n}，目标架构没有定义'})
    return flags


# ------------------------------------------------------------------ C2
def c2a(base, head, arch):
    flags, facts = [], []
    added = [(f, t) for f, h in hunks(base, head, f'arch/{arch}') for s, t in h if s == '+']
    for f, t in added:
        for fn, expr in re.findall(r'\b(kfree|kfree_sensitive|kvfree|vfree|free_pages|free_page)\s*\(\s*([^),]+)', t):
            key = re.sub(r'\s+', '', expr).replace('->', '.')
            tail = '.'.join(key.split('.')[-2:])
            folder = f.rsplit('/', 1)[0]
            found = []
            for path in [p for p in arch_files(head, arch) if p.startswith(folder)]:
                for m in re.finditer(r'([\w\.\->\[\]]+)\s*=\s*(\w+)\s*\(', show(head, path)):
                    lhs = re.sub(r'\s+', '', m.group(1)).replace('->', '.')
                    if m.group(2) in ALLOC and (lhs == key or lhs.endswith('.' + tail) or lhs == tail):
                        found.append((path, m.group(0), ALLOC[m.group(2)]))
            for path, stmt, family in found[:3]:
                facts.append(f'`{path}`中分配{expr.strip()}：`{stmt.strip()}…`')
            if found and all(family != FREE[fn] for _, _, family in found):
                flags.append({'check': 'C2a', 'where': f, 'what': f'用{fn}释放{expr.strip()}，但它由'
                              + '、'.join(sorted({s.split("=")[1].split("(")[0].strip() for _, s, _ in found}))
                              + '分配，释放函数不配对'})
    return flags, facts


def c2b(base, head, arch):
    flags = []
    for path, n in sorted(PC.changed_functions(base, head)):
        if not path.startswith(f'arch/{arch}/') or not path.endswith('.c'):
            continue
        mine = prototypes(show(head, path), [n]).get(n)
        if not mine:
            continue
        decl = None
        for p in CK.git('grep', '-l', '-w', n, base, '--', *COMMON).split()[:20]:
            decl = prototypes(show(base, p.split(':', 1)[1]), [n]).get(n)
            if decl:
                break
        if decl and (decl[0] != mine[0] or decl[1] != mine[1]):
            flags.append({'check': 'C2b', 'where': f'{path}:{n}',
                          'what': f'{n}定义为“{mine[0]}，{mine[1]}个参数”，公共代码声明为“{decl[0]}，{decl[1]}个参数”'})
        elif not decl and n.startswith('arch_') and not CK.git('grep', '-l', '-w', n, base, '--', *COMMON).strip():
            flags.append({'check': 'C2b', 'where': f'{path}:{n}', 'what': f'公共代码中没有{n}的声明或调用，可能是已删除的旧钩子'})
    return flags


def c2c(base, head, arch):
    facts = []
    plus = [t for _, h in hunks(base, head, f'arch/{arch}') for s, t in h if s == '+']
    minus = [t for _, h in hunks(base, head, f'arch/{arch}') for s, t in h if s == '-']
    called = {n for t in plus for n in re.findall(r'\b([A-Za-z_]\w*)\s*\(', t)} - \
             {n for t in minus for n in re.findall(r'\b([A-Za-z_]\w*)\s*\(', t)} - KEYWORDS
    for n in sorted(called)[:15]:
        hits = CK.git('grep', '-n', '-E', rf'^[A-Za-z_].*\b{n}\s*\([^)]*\)?\s*;?\s*$', base, '--', 'include/linux').splitlines()
        if hits:
            _, path, line, text = hits[0].split(':', 3)
            facts.append(f'`{n}`的原型（{path}:{line}）：`{text.strip()}`')
    members = {m for t in plus for m in re.findall(r'(?:->|\.)([a-z_]\w*)\b(?!\s*\()', t)} - \
              {m for t in minus for m in re.findall(r'(?:->|\.)([a-z_]\w*)\b(?!\s*\()', t)}
    for m in sorted(members)[:10]:
        hits = CK.git('grep', '-n', '-E', rf'^\s+[A-Za-z_][\w \*]*\b{m}(\[[^]]*\])?\s*;', base, '--',
                      f'arch/{arch}/include', 'include/linux').splitlines()
        if hits:
            _, path, line, text = hits[0].split(':', 3)
            facts.append(f'成员`{m}`的定义（{path}:{line}）：`{text.strip()}`')
    return facts


def check(base, head, arch, refs, ref_arch):
    flags = c1a(base, head, arch) + c1b(base, head, arch) + c1c(base, head, arch) + c1d(base, head, arch, refs, ref_arch)
    f2a, facts = c2a(base, head, arch)
    flags += f2a + c2b(base, head, arch)
    return {'flags': flags, 'facts': facts + c2c(base, head, arch)}
