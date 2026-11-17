"""Conservative lexical declaration extents; unsupported rows stay explicit."""
import bisect
import re

TOKEN = re.compile(r'[A-Za-z_]\w*|\d+|[^\s]')
IDENT = re.compile(r'^[A-Za-z_]\w*$')
ATTR = {'__attribute__', '__attribute', '__section', '__aligned', '__printf',
        '__scanf', '__alloc_size', '__counted_by', '__designated_init',
        '__assume', '__diagnose_if', '__cleanup'}
KEYWORDS = {'struct', 'union', 'enum', 'typedef', 'static', 'extern', 'const',
            'volatile', 'unsigned', 'signed', 'long', 'short', 'int', 'char',
            'void', 'bool', 'inline', 'typeof', '__typeof__', '__weak',
            '__ro_after_init', '__read_mostly', '__initdata', '__initconst',
            '__cacheline_aligned', '__cacheline_aligned_in_smp', '__maybe_unused',
            '__used', '__percpu', '__visible', '__attribute__'}

def scrub(text,keep_literals=False):
    # Preserve offsets/newlines. Literals must not create fake braces/declarations.
    pattern = r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda m: m[0] if keep_literals and not m[0].startswith(('/',)) else ''.join('\n' if c == '\n' else ' ' for c in m[0]),
                  text, flags=re.S)

def declarations(text):
    clean = scrub(text)
    newlines = [-1] + [m.start() for m in re.finditer('\n', text)]
    lineno = lambda pos: bisect.bisect_left(newlines, pos)
    rows = []
    masked = list(clean)
    offset = 0
    src = text.splitlines(keepends=True)
    i = 0
    while i < len(src):
        line = src[i]
        start = i
        if re.match(r'^\s*#', line):
            group = line
            while src[i].rstrip('\r\n').endswith('\\') and i + 1 < len(src):
                i += 1
                group += src[i]
            m = re.match(r'\s*#\s*define\s+([A-Za-z_]\w*)', group)
            if m:
                rows.append({'kind': 'macro', 'name': m[1], 'start': start + 1,
                             'end': i + 1, 'body_start': start + 1})
            length = len(group)
            masked[offset:offset + length] = ['\n' if c == '\n' else ' ' for c in group]
            offset += length
        else:
            offset += len(line)
        i += 1
    code = ''.join(masked)
    tok = [(m[0], m.start()) for m in TOKEN.finditer(code)]
    stack = []
    pairs = {}
    errors = []
    for j, (t, pos) in enumerate(tok):
        if t in '({[':
            stack.append((t, j))
        elif t in ')}]':
            want = {')': '(', '}': '{', ']': '['}[t]
            if stack and stack[-1][0] == want:
                _, k = stack.pop()
                pairs[k] = j
            else:
                errors.append({'line': lineno(pos), 'reason': 'unbalanced_conditional_syntax'})
    for _, j in stack:
        errors.append({'line': lineno(tok[j][1]), 'reason': 'unclosed_delimiter'})

    def emit(kind, name, a, b, body=None):
        if not name:
            return
        rows.append({'kind': kind, 'name': name, 'start': lineno(tok[a][1]),
                     'end': lineno(tok[b][1]),
                     'body_start': lineno(tok[body if body is not None else a][1])})

    # One external declaration at a time. Jump over matched nested expressions.
    a = j = 0
    while j < len(tok):
        t = tok[j][0]
        if t == ';':
            header = [x[0] for x in tok[a:j]]
            if header:
                eq = header.index('=') if '=' in header else len(header)
                left = header[:eq]
                if 'typedef' in left:
                    names = [v for v in left if IDENT.match(v) and v not in KEYWORDS]
                    if names: emit('typedef', names[-1], a, j)
                elif '(' not in left:
                    names = [v for v in left if IDENT.match(v) and v not in KEYWORDS]
                    if len(names) >= 1:
                        # Ignore variable array bounds when choosing the object name.
                        if '[' in left:
                            left = left[:left.index('[')]
                            names = [v for v in left if IDENT.match(v) and v not in KEYWORDS]
                        if names: emit('object', names[-1], a, j)
                elif '=' in header:
                    # Attribute groups after an object declarator are not its name.
                    cut = next((q for q,v in enumerate(left) if v in ATTR),len(left))
                    names = [v for v in left[:cut] if IDENT.match(v) and v not in KEYWORDS]
                    if names: emit('object', names[-1], a, j)
            a = j + 1
        elif t == '{' and j in pairs:
            end = pairs[j]
            header = [x[0] for x in tok[a:j]]
            # A function signature must have a named parameter group before its body.
            candidates = []
            q = a
            while q < j:
                if tok[q][0] == '(' and q in pairs:
                    if q > a and IDENT.match(tok[q - 1][0]) and tok[q - 1][0] not in ATTR | KEYWORDS:
                        candidates.append(tok[q - 1][0])
                    q = pairs[q] + 1
                else:
                    q += 1
            if candidates and '=' not in header and not any(v in header for v in ('typedef',)):
                name = candidates[0]
                # Macro-generated declarations are not guessed as ordinary functions.
                if name.isupper() or name.startswith(('SYSCALL_DEFINE', 'COMPAT_SYSCALL_DEFINE', 'DEFINE_')):
                    errors.append({'line': lineno(tok[a][1]), 'end': lineno(tok[end][1]),
                                   'reason': 'macro_generated_function', 'name': name})
                else:
                    emit('function', name, a, end, j)
                j = end
                a = j + 1
            elif '=' in header:
                eq = header.index('=')
                left = header[:eq]
                if '[' in left: left = left[:left.index('[')]
                names = [v for v in left if IDENT.match(v) and v not in KEYWORDS]
                stop = end + 1
                while stop < len(tok) and tok[stop][0] != ';': stop += 1
                if names: emit('object', names[-1], a, min(stop, len(tok)-1), j)
                j = min(stop, len(tok)-1)
                a = j + 1
            elif any(v in header for v in ('struct', 'union', 'enum')):
                for kind in ('struct', 'union', 'enum'):
                    if kind in header:
                        k = header.index(kind)
                        if k + 1 < len(header) and IDENT.match(header[k+1]):
                            emit(kind, header[k+1], a, end, j)
                # Enumeration constants are entities too.
                if 'enum' in header:
                    first = True
                    for q in range(j+1, end):
                        if first and IDENT.match(tok[q][0]):
                            emit('enum_constant', tok[q][0], q, q)
                            first = False
                        if tok[q][0] == ',': first = True
                stop = end + 1
                while stop < len(tok) and tok[stop][0] != ';': stop += 1
                tail = [v for v, _ in tok[end+1:stop] if IDENT.match(v) and v not in KEYWORDS]
                if tail:
                    emit('typedef' if 'typedef' in header else 'object', tail[0], a,
                         min(stop, len(tok)-1))
                j = min(stop, len(tok)-1)
                a = j + 1
            else:
                errors.append({'line': lineno(tok[a][1]), 'end': lineno(tok[end][1]),
                               'reason': 'unrecognized_external_brace'})
                j = end
                a = j + 1
        elif t in ('(', '[') and j in pairs:
            j = pairs[j]
        j += 1
    return rows, errors

def changed_lines(patch):
    result = []
    file = None
    old = new = None
    for line in patch.splitlines():
        if line.startswith('diff --git '):
            file = {'old_path': line.split()[2][2:], 'new_path': line.split()[3][2:],
                    'old_lines': [], 'new_lines': [], 'hunks': []}
            result.append(file)
            old = new = None
        elif line.startswith('@@ '):
            m = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            old, new = int(m[1]), int(m[2])
            file['hunks'].append(line)
        elif old is not None and line and line[0] in ' +-':
            if line[0] == '-':
                file['old_lines'].append(old)
                old += 1
            elif line[0] == '+':
                file['new_lines'].append(new)
                new += 1
            else:
                old += 1
                new += 1
    return result

