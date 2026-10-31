"""Direction 1, part 1 (criteria.md): mine assertion-style checks in common code and classify their conditions. WSL; counts only.
Output: relations.json (every site with its flags) and prints the counts.
"""
from pathlib import Path
import json
import re
import subprocess
from collections import Counter

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
END = 'df2908090cda'
EXCLUDE = (':!arch/', ':!tools/', ':!Documentation/', ':!samples/', ':!scripts/')
KINDS = ('BUILD_BUG_ON_MSG', 'BUILD_BUG_ON', 'static_assert', '_Static_assert', 'WARN_ON_ONCE', 'WARN_ON', 'WARN_ONCE', 'WARN',
         'VM_BUG_ON', 'VM_WARN_ON_ONCE', 'VM_WARN_ON', 'BUG_ON')
SITE = re.compile(r'\b(%s)\s*\(' % '|'.join(KINDS))
OPAQUE = ('sizeof', 'offsetof', 'sizeof_field', '__alignof__', 'ARRAY_SIZE', 'BIT', 'BIT_ULL', 'GENMASK', 'ilog2', 'order_base_2', 'is_power_of_2')
LAYOUT = ('sizeof', 'offsetof', 'sizeof_field', '__alignof__')
IDENT = re.compile(r'\b[A-Za-z_]\w*\b')
NUMBER = re.compile(r'\b(0[xX][0-9a-fA-F]+|\d+)[uUlL]*\b')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def blobs(paths):
    """{path: text} at END via one cat-file --batch."""
    req = ''.join('%s:%s\n' % (END, p) for p in paths).encode()
    raw = subprocess.run(['git', '-C', REPO, 'cat-file', '--batch'], input=req, capture_output=True).stdout
    out, pos = {}, 0
    for p in paths:
        nl = raw.index(b'\n', pos)
        head = raw[pos:nl].split()
        if len(head) < 3 or head[1] != b'blob':
            pos = nl + 1
            continue
        size = int(head[2])
        out[p] = raw[nl + 1:nl + 1 + size].decode('utf-8', 'replace')
        pos = nl + 1 + size + 1
    return out


def first_arg(text, i):
    """First argument of the call whose '(' is at text[i]; skips string/char literals. None if unbalanced."""
    depth, j, n = 0, i, len(text)
    while j < n:
        ch = text[j]
        if ch in '"\'':
            k = j + 1
            while k < n and text[k] != ch:
                k += 2 if text[k] == '\\' else 1
            j = k + 1
            continue
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
        elif ch == ',' and depth == 1:
            return text[i + 1:j]
        j += 1
    return None


def strip_opaque(expr):
    """Replace the argument lists of OPAQUE function-like names with '()' so their contents are not classified."""
    out, i = [], 0
    for m in re.finditer(r'\b(%s)\s*\(' % '|'.join(OPAQUE), expr):
        if m.start() < i:
            continue
        depth, j = 0, m.end() - 1
        while j < len(expr):
            depth += expr[j] == '('
            depth -= expr[j] == ')'
            if depth == 0:
                break
            j += 1
        out.append(expr[i:m.end() - 1] + '()')
        i = j + 1
    out.append(expr[i:])
    return ''.join(out)


def has_comparison(expr):
    e = expr.replace('->', ' ').replace('<<', ' ').replace('>>', ' ')
    return bool(re.search(r'<=|>=|==|!=|<|>', e))


def arch_macros():
    names = set()
    for line in git('grep', '-h', '-o', '-E', r'^\s*#\s*define\s+[A-Za-z_]\w*', END, '--', 'arch/*/include/*').splitlines():
        m = re.search(r'define\s+([A-Za-z_]\w*)', line)
        if m:
            names.add(m.group(1))
    return names


def main():
    target = HERE / 'relations.json'
    if target.exists():
        raise SystemExit('preserve')
    hits = {}
    for line in git('grep', '-n', '-E', r'\b(%s)\s*\(' % '|'.join(KINDS), END, '--', '*.c', '*.h', *EXCLUDE).splitlines():
        parts = line.split(':', 3)
        if len(parts) == 4 and not re.match(r'\s*#\s*define', parts[3]):
            hits.setdefault(parts[1], set()).add(int(parts[2]))
    texts = blobs(sorted(hits))
    amac = arch_macros()
    sites = []
    for path, lines in sorted(hits.items()):
        text = texts.get(path)
        if text is None:
            continue
        starts = [0]
        for k, ch in enumerate(text):
            if ch == '\n':
                starts.append(k + 1)
        for ln in sorted(lines):
            seg_start = starts[ln - 1]
            seg_end = starts[ln] if ln < len(starts) else len(text)
            for m in SITE.finditer(text[seg_start:seg_end]):
                cond = first_arg(text, seg_start + m.end() - 1)
                if cond is None:
                    continue
                cond = ' '.join(cond.split())
                bare = strip_opaque(cond)
                idents = [t for t in IDENT.findall(NUMBER.sub(' ', bare)) if t not in OPAQUE]
                const = all(re.fullmatch(r'[A-Z_][A-Z0-9_]*', t) for t in idents)
                arch = any(t in amac for t in idents) or any(re.search(r'\b%s\b' % k, cond) for k in LAYOUT)
                cmp_ = has_comparison(bare)
                sites.append({'path': path, 'line': ln, 'kind': m.group(1), 'cond': cond, 'comparison': cmp_, 'constant': const,
                              'arch_related': arch, 'candidate': cmp_ and const and arch})
    cand = [s for s in sites if s['candidate']]
    stats = {'sites': len(sites), 'comparison': sum(s['comparison'] for s in sites), 'constant': sum(s['constant'] for s in sites),
             'arch_related': sum(s['arch_related'] for s in sites), 'candidates': len(cand),
             'candidates_by_kind': dict(Counter(s['kind'] for s in cand)), 'sites_by_kind': dict(Counter(s['kind'] for s in sites)),
             'candidate_files': len({s['path'] for s in cand}),
             'candidates_in_c': sum(s['path'].endswith('.c') for s in cand), 'candidates_in_h': sum(s['path'].endswith('.h') for s in cand),
             'arch_macro_names': len(amac)}
    target.write_text(json.dumps({'stats': stats, 'sites': sites}, indent=1) + '\n')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
