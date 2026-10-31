"""Helpers for the cross-architecture sibling dataset: strict function-header names, body-edit targets, patch ids.

``function_spans_strict`` is ``candidate_bridge.function_spans`` with a stricter header name: only the last
statement fragment before ``{`` is read, names are identifiers directly before ``(`` at parenthesis depth 0,
control keywords and attribute-like words are skipped, and the fragment must end with ``)`` (trailing
qualifiers allowed). Anything else gets ``None``. ``named_spans`` keeps only the first branch of each
conditional so braces split across ``#if``/``#else`` stay balanced. Both recognisers take the header from
``candidate_bridge.header_window``; ``window=4`` reproduces the fixed four-line window used before 2026-10-31
(frozen methods and earlier rounds were run with it).
"""

from __future__ import annotations

import re
import subprocess

from .candidate_bridge import header_window

NOT_FUNCTION_NAMES = frozenset({
    "if", "for", "while", "switch", "return", "sizeof", "do", "else", "case", "typeof", "__typeof__", "__typeof",
    "asm", "__asm__", "__asm", "__attribute__", "__attribute", "defined", "_Static_assert", "static_assert",
    "__section__", "__aligned__", "__alignof__", "_Alignof", "offsetof",
})
_STRING = re.compile(r"//.*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")
_TRAILING = re.compile(r"(?:\s+(?:__\w+|const|noexcept)(?:\s*\(\([^;{}]*\)\))?)*\s*$")


def header_name(window: str) -> str | None:
    """Function name of a header fragment (text before ``{``), or None when it does not look like a header."""
    frag = re.split(r"[;}]", _STRING.sub(" ", window))[-1]
    names, depth, i = [], 0, 0
    for m in re.finditer(r"[()]|\b[A-Za-z_]\w*\b", frag):
        tok = m.group(0)
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
        elif depth == 0 and re.match(r"\s*\(", frag[m.end():]) and tok not in NOT_FUNCTION_NAMES:
            names.append(tok)
    core = _TRAILING.sub("", frag).rstrip()
    if not names or depth != 0 or not core.endswith(")"):
        return None
    return names[-1]


def function_spans_strict(text: str, window: int | None = None) -> list[tuple[int, int, str | None]]:
    """Top-level brace spans (first line, last line, header name or None), counted on the text as given;
    ``window`` as in candidate_bridge.header_window."""
    out, depth, start, header = [], 0, None, None
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        code = _STRING.sub("", line)
        if depth == 0 and "{" in code:
            start, header = n, header_name(header_window(lines, n, window))
        depth += code.count("{") - code.count("}")
        if depth == 0 and start is not None:
            out.append((start, n, header))
            start = None
    return out


def first_branch_only(c_text: str) -> str:
    """Blank preprocessor directives and every #elif/#else branch, keeping line numbers, so braces split across
    conditional branches stay balanced."""
    out, skip, cont = [], [], False
    for line in c_text.splitlines():
        is_dir = cont or line.lstrip().startswith("#")
        if is_dir and not cont:
            word = re.match(r"\s*#\s*(\w*)", line).group(1)
            if word in ("if", "ifdef", "ifndef"):
                skip.append(False)
            elif word in ("elif", "else") and skip:
                skip[-1] = True
            elif word == "endif" and skip:
                skip.pop()
        out.append("" if is_dir or any(skip) else line)
        cont = is_dir and line.rstrip().endswith("\\")
    return "\n".join(out) + "\n"


def named_spans(text: str, window: int | None = None) -> list[tuple[int, int, str]]:
    """Strict spans with a name, on the first branch of every conditional (line numbers kept)."""
    return [(s, e, h) for s, e, h in function_spans_strict(first_branch_only(text), window) if h]


def patch_id(repo: str, commit: str) -> str | None:
    """``git patch-id --stable`` of a commit, or None for an empty patch."""
    show = subprocess.run(["git", "-C", repo, "show", commit], capture_output=True).stdout
    out = subprocess.run(["git", "-C", repo, "patch-id", "--stable"], input=show, capture_output=True).stdout.decode().split()
    return out[0] if out else None
