"""Path conditions of call sites in a C function body.

A small statement parser over a token stream with comments, string/char literals and preprocessor lines removed.
For every call (an identifier followed by '(' that is not a keyword) it records the enclosing branch conditions as
(text, polarity) pairs: polarity True inside the then-branch of ``if (cond)``, False inside its else-branch, and
False for statements that follow ``if (cond) <exits>;`` without an else in the same or an enclosing block, where
<exits> ends with return, continue, break or goto. Loop and switch headers add no condition. Calls inside an if
condition also record the condition text before the call, for guards such as ``!pte_present(x) || ...``.

Condition texts are the tokens joined with single spaces, e.g. ``! pte_present ( pte )``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

KEYWORDS = {'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'return', 'goto', 'break', 'continue',
            'sizeof', 'typeof', '__typeof__', 'alignof', '_Alignof', '__alignof__', 'asm', '__asm__', 'defined',
            '__builtin_expect', 'offsetof'}
EXITS = {'return', 'continue', 'break', 'goto'}
TOKEN = re.compile(r'[A-Za-z_]\w*|0[xX][0-9a-fA-F]+\w*|\d+\w*|->|\+\+|--|&&|\|\||[<>=!]=|<<=?|>>=?|\S')
_STRIP = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)


@dataclass
class Call:
    name: str
    line: int                                   # 1-based line in the text given to analyze()
    args: list[str]                             # top-level argument texts
    conds: tuple[tuple[str, bool], ...]         # enclosing (condition text, polarity), outermost first
    cond_prefix: str | None = None              # if the call sits in an if condition: condition text before it


@dataclass
class Occurrence:
    name: str
    line: int                                   # 1-based line in the text given to occurrences()
    conds: tuple[tuple[str, bool], ...]


@dataclass
class _State:
    toks: list[tuple[str, int]]
    calls: list[Call] = field(default_factory=list)
    idents: list[Occurrence] = field(default_factory=list)


def strip_code(text: str) -> str:
    """Blank out comments, string/char literals and preprocessor lines, keeping line numbers."""
    def blank(m: re.Match) -> str:
        s = m.group(0)
        if s.startswith('"'):
            return '""'
        if s.startswith("'"):
            return "' '"
        return re.sub(r'[^\n]', ' ', s)
    text = _STRIP.sub(blank, text)
    out, cont = [], False
    for line in text.split('\n'):
        if cont or line.lstrip().startswith('#'):
            cont = line.rstrip().endswith('\\')
            out.append('')
        else:
            out.append(line)
    return '\n'.join(out)


def tokenize(text: str) -> list[tuple[str, int]]:
    toks = []
    for n, line in enumerate(strip_code(text).split('\n'), 1):
        toks += [(t, n) for t in TOKEN.findall(line) if t not in ('"', "'")]
    return toks


def analyze(text: str) -> list[Call]:
    """Calls with path conditions for the first function body (first top-level '{ ... }') in text."""
    return _parse(text).calls


def occurrences(text: str, names: set[str]) -> list[Occurrence]:
    """Every occurrence of an identifier in names within the first function body, with its path conditions."""
    return [o for o in _parse(text).idents if o.name in names]


def _parse(text: str) -> _State:
    toks = tokenize(text)
    st = _State(toks)
    depth = 0
    for i, (t, _) in enumerate(toks):
        if t == '(':
            depth += 1
        elif t == ')':
            depth -= 1
        elif t == '{' and depth == 0:
            _block(st, i + 1, ())
            break
    return st


def params(text: str) -> list[str]:
    """Parameter names of the first function header in text (last identifier of each parameter)."""
    toks = [t for t, _ in tokenize(text)]
    try:
        start = next(i for i, t in enumerate(toks) if t == '(')
    except StopIteration:
        return []
    end = _match(toks, start)
    names, cur = [], []
    for t in toks[start + 1:end] + [',']:
        if t == ',':
            ids = [x for x in cur if re.fullmatch(r'[A-Za-z_]\w*', x)]
            if ids and ids != ['void']:
                names.append(ids[-1])
            cur = []
        elif t not in ('[', ']') and not t.isdigit():
            cur.append(t)
    return names


def _match(toks: list, i: int) -> int:
    """Index of the bracket closing toks[i]."""
    pairs = {'(': ')', '[': ']', '{': '}'}
    want, depth = [], 0
    for j in range(i, len(toks)):
        t = toks[j] if isinstance(toks[j], str) else toks[j][0]
        if t in pairs:
            want.append(pairs[t])
        elif want and t == want[-1]:
            want.pop()
            if not want:
                return j
    return len(toks) - 1


def _text(st: _State, a: int, b: int) -> str:
    return ' '.join(t for t, _ in st.toks[a:b])


def _record(st: _State, a: int, b: int, conds: tuple, in_cond: int | None = None) -> None:
    """Record every call and identifier in toks[a:b]; in_cond is the index where the enclosing if condition starts."""
    toks = st.toks
    for i in range(a, b):
        t = toks[i][0]
        if re.fullmatch(r'[A-Za-z_]\w*', t) and t not in KEYWORDS:
            st.idents.append(Occurrence(t, toks[i][1], conds))
        if i + 1 < b and toks[i + 1][0] == '(' and re.fullmatch(r'[A-Za-z_]\w*', t) and t not in KEYWORDS:
            end = _match(toks, i + 1)
            args, cur, depth = [], [], 0
            for j in range(i + 2, end):
                tj = toks[j][0]
                if tj in '([{':
                    depth += 1
                elif tj in ')]}':
                    depth -= 1
                if tj == ',' and depth == 0:
                    args.append(' '.join(cur))
                    cur = []
                else:
                    cur.append(tj)
            if cur:
                args.append(' '.join(cur))
            prefix = _text(st, in_cond, i) if in_cond is not None else None
            st.calls.append(Call(t, toks[i][1], args, conds, prefix))


def _block(st: _State, i: int, conds: tuple) -> tuple[int, bool]:
    """Parse statements until the matching '}'; returns (index after '}', block ends with an exit)."""
    toks, running, last_exit = st.toks, conds, False
    while i < len(toks) and toks[i][0] != '}':
        i, last_exit, early = _stmt(st, i, running)
        if early is not None:
            running = running + (early,)
    return i + 1, last_exit


def _stmt(st: _State, i: int, conds: tuple) -> tuple[int, bool, tuple[str, bool] | None]:
    """Parse one statement at toks[i]. Returns (next index, statement always exits, early-exit condition)."""
    toks = st.toks
    if i >= len(toks):
        return i, False, None
    t = toks[i][0]
    if t == '{':
        j, ex = _block(st, i + 1, conds)
        return j, ex, None
    if t == ';':
        return i + 1, False, None
    if t == 'if':
        close = _match(toks, i + 1)
        cond = _text(st, i + 2, close)
        _record(st, i + 2, close, conds, in_cond=i + 2)
        j, then_exit, _ = _stmt(st, close + 1, conds + ((cond, True),))
        if j < len(toks) and toks[j][0] == 'else':
            k, else_exit, _ = _stmt(st, j + 1, conds + ((cond, False),))
            return k, then_exit and else_exit, None
        return j, False, ((cond, False) if then_exit else None)
    if t in ('for', 'while', 'switch') and i + 1 < len(toks) and toks[i + 1][0] == '(':
        close = _match(toks, i + 1)
        _record(st, i + 2, close, conds)
        j, _, _ = _stmt(st, close + 1, conds)
        return j, False, None
    if t == 'do':
        j, _, _ = _stmt(st, i + 1, conds)
        if j < len(toks) and toks[j][0] == 'while':
            close = _match(toks, j + 1)
            _record(st, j + 2, close, conds)
            j = close + 1
        return (j + 1 if j < len(toks) and toks[j][0] == ';' else j), False, None
    if t in ('case', 'default'):
        j = i
        while j < len(toks) and toks[j][0] != ':':
            j += 1
        return j + 1, False, None
    if re.fullmatch(r'[A-Za-z_]\w*', t) and i + 1 < len(toks) and toks[i + 1][0] == ':' and t not in KEYWORDS:
        return i + 2, False, None   # label
    # expression or declaration statement; an identifier call followed by '{' is a loop-like macro
    j, depth = i, 0
    while j < len(toks):
        tj = toks[j][0]
        if tj in '([':
            depth += 1
        elif tj in ')]':
            depth -= 1
        elif tj == '{':
            if depth == 0 and j > i and toks[j - 1][0] == ')':
                _record(st, i, j, conds)
                k, _, _ = _stmt(st, j, conds)
                return k, False, None
            j = _match(toks, j)   # initializer or statement expression
        elif tj == ';' and depth == 0:
            break
        elif tj == '}' and depth == 0:
            break   # missing ';' before block end
        j += 1
    _record(st, i, j, conds)
    return (j + 1 if j < len(toks) and toks[j][0] == ';' else j), t in EXITS, None
