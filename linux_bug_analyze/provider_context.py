"""Method change M1: provider-side macro definitions for the E1 input (rules in
experiments/case_taxonomy/e1_provider_context_20261028/registration.md).

From full -dD macro traces of each touched .c file in several build contexts, select the macros the file
consumes whose expansion chain is architecture dependent, and render their final definitions per context.
Mechanical: no fix, commit message or known answer is consulted.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping

from .candidate_bridge import C_WORDS

CONFIG_CAP = 12
CHAIN_DEPTH = 3
BUDGET = 24_000


def _code(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return re.sub(r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', " ", text)


def guard_configs(c_text: str) -> list[str]:
    """CONFIG_* symbols in preprocessor conditionals, most frequent first (ties by name), at most CONFIG_CAP."""
    counts = Counter(s for line in _code(c_text).splitlines() if re.match(r"\s*#\s*(?:if|ifdef|ifndef|elif)\b", line)
                     for s in re.findall(r"\bCONFIG_([A-Z0-9_]+)\b", line))
    return [s for s, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:CONFIG_CAP]


def pasted_names(c_text: str) -> list[str]:
    """Names produced by ## in function-like macros defined in this file, at their invocation sites."""
    return [name for inv in pasted_invocations(c_text) for name, _ in inv["names"]]


def pasted_invocations(c_text: str) -> list[dict[str, Any]]:
    """Each invocation of a ##-pasting function-like macro defined in this file, with the names it pastes
    (name, index of the argument it came from)."""
    code = _code(c_text).replace("\\\n", " ")
    out = []
    for m in re.finditer(r"^\s*#\s*define\s+([A-Za-z_]\w*)\(([^)]*)\)(.*)$", code, re.M):
        name, params, body = m.group(1), [p.strip() for p in m.group(2).split(",")], m.group(3)
        if "##" not in body:
            continue
        patterns = []
        for i, p in enumerate(params):
            for pm in re.finditer(r"(\w*)\s*##\s*" + re.escape(p) + r"\b(?:\s*##\s*(\w+))?", body):
                patterns.append((i, pm.group(1), pm.group(2) or ""))
            for pm in re.finditer(r"\b" + re.escape(p) + r"\s*##\s*(\w+)", body):
                patterns.append((i, "", pm.group(1)))
        for call in re.finditer(r"\b" + re.escape(name) + r"\s*\(([^()]*)\)", code[m.end():]):
            args = [a.strip() for a in call.group(1).split(",")]
            names = [(prefix + args[i] + suffix, i) for i, prefix, suffix in patterns if i < len(args) and re.fullmatch(r"\w+", args[i])]
            out.append({"macro": name, "args": args, "names": names})
    return out


def consumed(c_text: str) -> Counter:
    """Identifier use counts in the touched file, plus ##-pasted names."""
    toks = Counter(t for t in re.findall(r"\b[A-Za-z_]\w*\b", _code(c_text)) if t not in C_WORDS)
    toks.update(pasted_names(c_text))
    return toks


def _body_macros(define: str | None, macros: Mapping[str, Any]) -> set[str]:
    if not define:
        return set()
    m = re.match(r"#\s*define\s+[A-Za-z_]\w*(\([^)]*\))?(.*)$", define)
    params = set(re.findall(r"\w+", m.group(1) or "")) if m else set()
    body = m.group(2) if m else ""
    return {t for t in re.findall(r"\b[A-Za-z_]\w*\b", body) if t not in params and (macros.get(t) or {}).get("defined")}


def arch_dependent(name: str, traces: Mapping[str, Mapping[str, Any]]) -> bool:
    """Final definition comes from arch/ in some context, or differs (text or presence) across contexts."""
    recs = [traces[c].get(name) or {} for c in traces]
    if any(r.get("defined") and (r.get("origin") or "").startswith("arch/") for r in recs):
        return True
    return len({(r.get("text") if r.get("defined") else None) for r in recs}) > 1


def chain(name: str, traces: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """``name`` plus the macros its definition bodies reference, transitively to CHAIN_DEPTH, in any context."""
    seen, frontier = [name], [name]
    for _ in range(CHAIN_DEPTH):
        nxt = []
        for n in frontier:
            for c in traces:
                for b in sorted(_body_macros((traces[c].get(n) or {}).get("define"), traces[c])):
                    if b not in seen:
                        seen.append(b)
                        nxt.append(b)
        frontier = nxt
    return seen


def select(traces: Mapping[str, Mapping[str, Any]], uses: Counter) -> list[dict[str, Any]]:
    """traces: context -> full macro trace. Returns selected macros (most used first) with arch-dependent chain members."""
    contexts = list(traces)
    out = []
    for name, count in sorted(uses.items(), key=lambda kv: (-kv[1], kv[0])):
        if not any((traces[c].get(name) or {}).get("defined") for c in contexts):
            continue
        members = [n for n in chain(name, traces) if arch_dependent(n, traces)]
        if members:
            out.append({"macro": name, "uses": count, "chain": members})
    return out


def render(selected: list[dict[str, Any]], traces: Mapping[str, Mapping[str, Any]], given: Mapping[str, str]) -> tuple[str, dict[str, Any]]:
    """Text for {PROVIDER_DEFINITIONS} within BUDGET; definitions already shown in the given sources are skipped."""
    given_lines = {(p, n) for p, t in given.items() for n in range(1, len(t.splitlines()) + 1)}
    blocks, used, truncated, listed = [], 0, 0, set()
    for item in selected:
        lines = []
        for name in [item["macro"]] + [n for n in item["chain"] if n != item["macro"]]:
            if name in listed:
                continue
            groups: dict[tuple, list[str]] = {}
            for ctx, trace in traces.items():
                r = trace.get(name) or {}
                key = (r.get("origin"), r.get("line"), r.get("define")) if r.get("defined") else (None, None, None)
                groups.setdefault(key, []).append(ctx)
            for (origin, line, define), ctxs in groups.items():
                if origin is None:
                    lines.append(f"  {', '.join(ctxs)}: (not defined)")
                elif (origin, line) in given_lines:
                    lines.append(f"  {', '.join(ctxs)}: {origin}:{line} (shown in the sources above)")
                else:
                    lines.append(f"  {', '.join(ctxs)}: {origin}:{line}  {define}")
            listed.add(name)
        if not lines:
            continue
        block = f"[{item['macro']}] used {item['uses']}x in the sources above\n" + "\n".join(lines) + "\n"
        if used + len(block.encode()) > BUDGET:
            truncated += 1
            continue
        blocks.append(block)
        used += len(block.encode())
    text = "\n".join(blocks) + (f"\n({truncated} further macros omitted for length)\n" if truncated else "")
    return text, {"selected": len(selected), "rendered": len(blocks), "truncated": truncated, "bytes": used}


def sparse_sources(selected: list[dict[str, Any]], traces: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    """Pseudo source texts holding only the rendered #define lines at their line numbers (so candidate references
    into provider files resolve in the bridge)."""
    files: dict[str, dict[int, str]] = {}
    for item in selected:
        for name in item["chain"] + [item["macro"]]:
            for trace in traces.values():
                r = trace.get(name) or {}
                if r.get("defined") and r.get("line"):
                    files.setdefault(r["origin"], {})[r["line"]] = r["define"]
    return {p: "\n".join(lines.get(n, "") for n in range(1, max(lines) + 1)) + "\n" for p, lines in files.items()}
