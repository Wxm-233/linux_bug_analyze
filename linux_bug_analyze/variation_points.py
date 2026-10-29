"""Method M4 variation points (m4_design_20261028/registration_m4_design.md, m4_coverage_20261029/clarification_m4_1.md).

Program-side "where to look": positions in a consumer .c file where behaviour may differ across architectures or
configurations, from the parent source and per-context macro traces / preprocessed function definitions.

V1 architecture-dependent macro use   V2 architecture/feature preprocessor conditional   V3 call to an architecture-
dependent function   V4 geometry/limit comparison   V5 C-level IS_ENABLED(CONFIG_<ARCH>) style branch
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping

from .candidate_bridge import C_WORDS, function_spans
from . import provider_context as pc

CAP = 16
PRIORITY = ("V2", "V5", "V4", "V3", "V1")
ARCH_VARIANTS = {"X86_64", "X86_32", "ARM64", "PPC", "PPC64", "SPARC64", "SPARC32", "UML"}
PREDEFINED = {"__x86_64__", "__i386__", "__aarch64__", "__arm__", "__s390__", "__s390x__", "__sparc__", "__riscv",
              "__powerpc__", "__powerpc64__", "__mips__", "__loongarch__", "__ia64__"}
FEATURE = re.compile(r"^(?:__HAVE_ARCH_|HAVE_ARCH_|__ARCH_HAS_|ARCH_HAS_)\w+$")
WIDTH = {"BITS_PER_LONG", "CONFIG_64BIT", "CONFIG_32BIT"}
GEOM = re.compile(r"(?:_ORDER|_SHIFT|_SIZE|_NR)$")
CMP = re.compile(r"(?<![-<>])(?:<=|>=|<|>)(?![<>])")
CONFIG_TEST = re.compile(r"\b(?:IS_ENABLED|IS_BUILTIN|IS_MODULE|IS_REACHABLE)\s*\(\s*(CONFIG_\w+)\s*\)")


def arch_names(arch_dirs: list[str]) -> set[str]:
    return {d.upper() for d in arch_dirs} | ARCH_VARIANTS


def _arch_token(tok: str, arches: set[str]) -> bool:
    if tok in PREDEFINED or tok in WIDTH or FEATURE.match(tok):
        return True
    return tok.startswith("CONFIG_") and tok[7:] in arches


def _code_lines(c_text: str) -> list[str]:
    """Source lines with comments and string literals blanked, line count preserved."""
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), c_text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return [re.sub(r'"(?:\\.|[^"\\])*"', '""', l) for l in text.splitlines()]


def _block_end(lines: list[str], start: int) -> int:
    depth = 0
    for n in range(start, len(lines)):
        d = re.match(r"\s*#\s*(if|ifdef|ifndef|endif)\b", lines[n])
        if d:
            depth += 1 if d.group(1) != "endif" else -1
            if depth == 0:
                return n + 1
    return len(lines)


def enumerate_sites(c_text: str, traces: Mapping[str, Mapping[str, Any]], tu_files: Mapping[str, Mapping[str, str]],
                    arches: set[str]) -> list[dict[str, Any]]:
    """All variation points (1-based lines). ``tu_files``: context -> {function: defining file (relative)}."""
    lines = _code_lines(c_text)
    sites: list[dict[str, Any]] = []
    macro_names = {n for t in traces.values() for n, r in t.items() if r.get("defined")}
    # V2: preprocessor conditionals naming architectures, arch features or word size
    for n, l in enumerate(lines):
        m = re.match(r"\s*#\s*(if|ifdef|ifndef|elif)\b(.*)$", l)
        if m:
            toks = [t for t in re.findall(r"\b[A-Za-z_]\w*\b", m.group(2)) if _arch_token(t, arches)]
            if toks:
                sites.append({"type": "V2", "key": "%d:%s" % (n + 1, ",".join(toks)), "lines": list(range(n + 1, _block_end(lines, n) + 1)),
                              "anchor": n + 1, "directive": m.group(1), "condition": m.group(2).strip(), "names": toks})
    # Function bodies (directive lines blanked so macro bodies are not functions)
    plain = "\n".join("" if l.lstrip().startswith("#") else l for l in lines) + "\n"
    spans = [(s, e, h) for s, e, h in function_spans(plain) if h]
    in_body = lambda n: any(s < n <= e for s, e, _ in spans)
    defined_here = {h for _, _, h in spans}
    calls: dict[str, list[int]] = {}
    for n, l in enumerate(lines, 1):
        if l.lstrip().startswith("#") or not in_body(n):
            continue
        # V5: C-level configuration tests on architecture/width symbols
        cfg = [c for c in CONFIG_TEST.findall(l) if _arch_token(c, arches)]
        if cfg:
            sites.append({"type": "V5", "key": "%d:%s" % (n, ",".join(cfg)), "lines": [n], "anchor": n,
                          "exprs": [m.group(0) for m in CONFIG_TEST.finditer(l) if m.group(1) in cfg]})
        # V4: comparisons involving a geometry/limit macro
        if CMP.search(l):
            g = [t for t in re.findall(r"\b[A-Za-z_]\w*\b", l) if t in macro_names and (GEOM.search(t) or "MAX" in t or "LIMIT" in t)]
            if g:
                sites.append({"type": "V4", "key": "%d:%s" % (n, ",".join(dict.fromkeys(g))), "lines": [n], "anchor": n, "macros": list(dict.fromkeys(g))})
        for f in re.findall(r"\b([A-Za-z_]\w*)\s*\(", l):
            if f not in C_WORDS and f not in macro_names and f not in defined_here:
                calls.setdefault(f, []).append(n)
    # V3: calls to functions whose definition differs across contexts
    for f, where in calls.items():
        files = [tu_files[c].get(f) for c in tu_files]
        if len(set(files)) > 1 or any((x or "").startswith("arch/") for x in files):
            sites.append({"type": "V3", "key": f, "lines": where, "anchor": where[0], "uses": len(where),
                          "definitions": {c: tu_files[c].get(f) for c in tu_files}})
    # V1: architecture-dependent macros (M1 selection), with use lines and ##-paste invocation lines
    uses = pc.consumed(c_text)
    # Whole logical #define lines (with their continuation lines) that paste with ##.
    defs, raw, n = [], c_text.splitlines(), 0
    while n < len(raw):
        if re.match(r"\s*#\s*define\b", raw[n]):
            end = n
            while end < len(raw) - 1 and raw[end].rstrip().endswith("\\"):
                end += 1
            if "##" in "\n".join(raw[n:end + 1]):
                defs.append("\n".join(raw[n:end + 1]))
            n = end
        n += 1
    paste_defs = "\n".join(defs)
    for item in pc.select(traces, uses):
        name = item["macro"]
        where = [n for n, l in enumerate(lines, 1) if re.search(r"\b%s\b" % re.escape(name), l)]
        if not where:
            where = [n for n, l in enumerate(c_text.splitlines(), 1)
                     if any(name == p for inv in pc.pasted_invocations(paste_defs + "\n" + l) for p, _ in inv["names"])]
        if where:
            sites.append({"type": "V1", "key": name, "lines": where, "anchor": where[0], "uses": item["uses"], "chain": item["chain"]})
    return sites


def select_sites(sites: list[dict[str, Any]], cap: int = CAP) -> list[dict[str, Any]]:
    """Clarification 1: V2 -> V5 -> V4 -> V3 -> V1; V2/V5/V4 by line, V3/V1 by use count; at most ``cap``."""
    out = []
    for t in PRIORITY:
        group = [s for s in sites if s["type"] == t]
        group.sort(key=(lambda s: (-s.get("uses", 0), s["anchor"])) if t in ("V3", "V1") else (lambda s: s["anchor"]))
        out += group
    return out[:cap]


def fix_ranges(diff_u0: str) -> list[tuple[int, int]]:
    """Parent line ranges of each hunk in a -U0 diff of one file (pure insertions give their insertion line)."""
    out = []
    for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", diff_u0, re.M):
        start, count = int(m.group(1)), int(m.group(2) or "1")
        out.append((start, start + max(count, 1) - 1) if count else (start, start))
    return out


def covers(site: Mapping[str, Any], ranges: list[tuple[int, int]], margin: int = 5) -> bool:
    return any(lo - margin <= n <= hi + margin for n in site["lines"] for lo, hi in ranges)
