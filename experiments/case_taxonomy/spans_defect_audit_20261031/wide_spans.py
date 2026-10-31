"""Corrected function-span recognisers for the audit (criteria.md): identical to candidate_bridge.function_spans and
sibling_pairs.function_spans_strict except that the header window reaches back to the previous line ending in ';' or
'}', a blank line or a preprocessor line (at most 15 lines) instead of a fixed 4 lines.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from linux_bug_analyze.sibling_pairs import _STRING, first_branch_only, header_name  # noqa: E402

LOOKBACK = 15


def window_start(lines, n):
    """0-based index of the first header line for the '{' on 1-based line n."""
    h = n
    while h > 1 and n - h < LOOKBACK:
        prev = lines[h - 2].strip()
        if not prev or prev.endswith((';', '}')) or prev.startswith('#'):
            break
        h -= 1
    return h - 1


def function_spans(text):
    """candidate_bridge.function_spans with the wide header window."""
    out, depth, start, header = [], 0, None, None
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        code = re.sub(r"//.*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", "", line)
        if depth == 0 and "{" in code:
            window = " ".join(lines[window_start(lines, n):n]).split("{")[0]
            names = re.findall(r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:__\w+\s*)*$", window)
            start, header = n, (names[-1] if names else None)
        depth += code.count("{") - code.count("}")
        if depth == 0 and start is not None:
            out.append((start, n, header))
            start = None
    return out


def function_spans_strict(text):
    """sibling_pairs.function_spans_strict with the wide header window."""
    out, depth, start, header = [], 0, None, None
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        code = _STRING.sub("", line)
        if depth == 0 and "{" in code:
            window = " ".join(lines[window_start(lines, n):n]).split("{")[0]
            start, header = n, header_name(window)
        depth += code.count("{") - code.count("}")
        if depth == 0 and start is not None:
            out.append((start, n, header))
            start = None
    return out


def named_spans(text):
    return [(s, e, h) for s, e, h in function_spans_strict(first_branch_only(text)) if h]
