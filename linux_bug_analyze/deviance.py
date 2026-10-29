"""Cross-configuration deviance mining (P0 part 2, experiments/case_taxonomy/p0_feasibility_20261029/registration_p0.md).

Candidates only: a relation that holds in most configuration contexts and fails in a few is ranked for review; it is
never treated as a specification. A1 integer-relation minority, A2 sibling-entity provenance minority, A3
preprocessor-condition minority.
"""

from __future__ import annotations

import ast
import operator
import re
from itertools import combinations
from typing import Any, Mapping

from . import provider_context as pc

CASTS = re.compile(r"\(\s*(?:const\s+)?(?:unsigned|signed)?\s*(?:long\s+long|long|int|short|char|u8|u16|u32|u64|s8|s16|s32|s64|"
                   r"size_t|unsigned)\s*\)")
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.LShift: operator.lshift, ast.RShift: operator.rshift, ast.BitAnd: operator.and_, ast.BitOr: operator.or_, ast.BitXor: operator.xor}
_CMP = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}


def _eval_ast(node: ast.AST) -> int:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        v = _eval_ast(node.operand)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.Invert):
            return ~v
        if isinstance(node.op, ast.Not):
            return int(not v)
        if isinstance(node.op, ast.UAdd):
            return v
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP:
        return int(_CMP[type(node.ops[0])](_eval_ast(node.left), _eval_ast(node.comparators[0])))
    if isinstance(node, ast.BoolOp):
        vals = [_eval_ast(v) for v in node.values]
        return int(all(vals)) if isinstance(node.op, ast.And) else int(any(vals))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("min", "max") and len(node.args) == 2:
        a, b = _eval_ast(node.args[0]), _eval_ast(node.args[1])
        return min(a, b) if node.func.id == "min" else max(a, b)
    raise ValueError("unsupported")


def evaluate(expr: str, trace: Mapping[str, Any], depth: int = 0, defined_only: bool = False) -> int | None:
    """Integer value of a C constant expression under one context's macro trace (object-like macros substituted
    recursively; min/max/BIT supported); None when anything is not reducible."""
    if depth > 12:
        return None
    text = re.sub(r"\bdefined\s*\(\s*(\w+)\s*\)|\bdefined\s+(\w+)",
                  lambda m: "1" if (trace.get(m.group(1) or m.group(2)) or {}).get("defined") else "0", expr)
    for _ in range(4):
        text = re.sub(r"\bBIT(?:_ULL)?\s*\(\s*([^()]*)\)", r"(1<<(\1))", text)
    text = CASTS.sub("", text)
    text = re.sub(r"\b(0[xX][0-9a-fA-F]+|\d+)(?:[uU]?[lL]{1,2}|[lL]{1,2}[uU]?|[uU])\b", r"\1", text)

    def sub(m: re.Match) -> str:
        name = m.group(0)
        if name in ("min", "max") or re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", name):
            return name
        rec = trace.get(name) or {}
        if not rec.get("defined"):
            return "0" if defined_only else "__undef__"
        define = rec.get("define") or ""
        if re.match(r"#\s*define\s+%s\(" % re.escape(name), define):
            return "__fnlike__"
        v = evaluate(rec.get("text") or "", trace, depth + 1)
        return "(%d)" % v if v is not None else "__undef__"

    text = re.sub(r"\b[A-Za-z_]\w*\b", sub, text)
    if "__undef__" in text or "__fnlike__" in text or not text.strip():
        return None
    text = text.replace("&&", " and ").replace("||", " or ").replace("/", "//").replace("!=", "__ne__").replace("!", " not ").replace("__ne__", "!=")
    try:
        return int(_eval_ast(ast.parse(text.strip(), mode="eval")))
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError, RecursionError):
        return None


UNIT_SUFFIXES = ("_ORDER", "_SHIFT", "_SIZE", "_NR")


def _unit(name: str) -> str | None:
    return next((s for s in UNIT_SUFFIXES if name.endswith(s)), None)


def a1_integer_minority(c_text: str, traces: Mapping[str, Mapping[str, Any]], min_contexts: int = 4,
                        same_unit: bool = False, reverse_limits: bool = False) -> list[dict[str, Any]]:
    """P0b switches: ``same_unit`` compares only names sharing a unit suffix; ``reverse_limits`` adds MAX/LIMIT macros
    whose expansion chain reaches the candidate pool."""
    uses = pc.consumed(c_text)
    names = {n for n in uses if any((t.get(n) or {}).get("defined") for t in traces.values())}
    pool = set(names)
    for n in names:
        pool |= set(pc.chain(n, traces))
    if reverse_limits:
        limits = {n for t in traces.values() for n, r in t.items() if r.get("defined") and ("MAX" in n or "LIMIT" in n)}
        pool |= {n for n in limits if set(pc.chain(n, traces)) & (pool - {n})}
    if same_unit:
        pool = {n for n in pool if _unit(n)}
    values = {n: {c: evaluate(n, t) for c, t in traces.items()} for n in sorted(pool)}
    values = {n: v for n, v in values.items() if sum(x is not None for x in v.values()) >= min_contexts}
    out = []
    for a, b in combinations(sorted(values), 2):
        if same_unit and _unit(a) != _unit(b):
            continue
        rel = {c: (lambda x, y: None if x is None or y is None else ("<" if x < y else "=" if x == y else ">"))(values[a][c], values[b][c]) for c in traces}
        known = {c: r for c, r in rel.items() if r is not None}
        if len(known) < min_contexts:
            continue
        counts = {r: sum(1 for x in known.values() if x == r) for r in set(known.values())}
        major = max(counts, key=lambda r: (counts[r], r))
        minority = sorted(c for c, r in known.items() if r != major)
        if minority and counts[major] * 3 >= 2 * len(known):
            out.append({"family": "A1", "key": "%s?%s" % (a, b), "majority": major, "minority": minority,
                        "score": counts[major] - len(minority), "values": {c: (values[a][c], values[b][c]) for c in traces}})
    return out


def a2_sibling_provenance(c_text: str, traces: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for inv in pc.pasted_invocations(c_text):
        groups.setdefault(inv["macro"], []).append(inv)
    out = []
    for macro, invs in groups.items():
        rows = []
        for inv in invs:
            pasted = [n for n, _ in inv["names"] if any((t.get(n) or {}).get("defined") for t in traces.values())]
            fb_ctx = sorted({c for n in pasted for c, t in traces.items() if (t.get(n) or {}).get("defined") and (t.get(n) or {}).get("fallback")})
            rows.append({"entity": inv["args"][0] if inv["args"] else "", "fallback_contexts": fb_ctx, "macros": pasted})
        fb = [r for r in rows if r["fallback_contexts"]]
        if fb and len(fb) * 2 <= len(rows):
            for r in fb:
                out.append({"family": "A2", "key": "%s(%s)" % (macro, r["entity"]), "minority": r["fallback_contexts"],
                            "score": len(rows) - len(fb), "siblings": len(rows), "macros": r["macros"]})
    return out


def a3_condition_minority(c_text: str, traces: Mapping[str, Mapping[str, Any]], arches: set[str]) -> list[dict[str, Any]]:
    from .variation_points import _arch_token
    out = []
    for n, line in enumerate(c_text.splitlines(), 1):
        m = re.match(r"\s*#\s*(if|ifdef|ifndef|elif)\b(.*)$", line)
        if not m or not [t for t in re.findall(r"\b[A-Za-z_]\w*\b", m.group(2)) if _arch_token(t, arches)]:
            continue
        kind, cond = m.group(1), m.group(2).strip()
        vals = {}
        for c, t in traces.items():
            if kind in ("ifdef", "ifndef"):
                d = bool((t.get(cond.split()[0]) or {}).get("defined"))
                vals[c] = int(d if kind == "ifdef" else not d)
            else:
                vals[c] = evaluate(cond, t, defined_only=True)
        known = {c: v for c, v in vals.items() if v is not None}
        if not known:
            continue
        counts = {v: sum(1 for x in known.values() if x == v) for v in set(known.values())}
        major = max(counts, key=lambda v: (counts[v], -v))
        minority = sorted(c for c, v in known.items() if v != major)
        if minority:
            out.append({"family": "A3", "key": "%d:#%s %s" % (n, kind, cond), "majority": major, "minority": minority,
                        "score": counts[major] - len(minority)})
    return out


def rank(cands: list[dict[str, Any]], top: int = 10) -> list[dict[str, Any]]:
    return sorted(cands, key=lambda c: (-c["score"], len(c["minority"]), c["family"], c["key"]))[:top]
