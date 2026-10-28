"""Method change M2: program-enumerated check families (rules in
experiments/case_taxonomy/check_families_20261028/registration.md).

F1 overridable-macro fallback consumed by an exported entity; F2 arch-dependent geometry macro vs a common
limit macro. Instances come from the consumer source and parent macro traces; each yields a contract over
bundle facts (emits_*, arch_provides_*, value_*, *_returns_only_zero) judged per build context by the core.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .candidate_bridge import function_spans
from .provider_context import arch_dependent, chain, consumed, pasted_invocations

GEOMETRY_SUFFIXES = ("_ORDER", "_SHIFT", "_SIZE", "_NR")


def _without_directives(c_text: str) -> str:
    """Blank preprocessor directives (with continuations) keeping line numbers, so macro bodies are not functions."""
    out, cont = [], False
    for line in c_text.splitlines():
        is_dir = cont or line.lstrip().startswith("#")
        out.append("" if is_dir else line)
        cont = is_dir and line.rstrip().endswith("\\")
    return "\n".join(out) + "\n"


def _functions(c_text: str) -> dict[str, str]:
    text = _without_directives(c_text)
    lines = text.splitlines()
    return {h: "\n".join(lines[s - 1:e]) for s, e, h in function_spans(text) if h}


def overridable(name: str, traces: Mapping[str, Mapping[str, Any]]) -> bool:
    recs = [traces[c].get(name) or {} for c in traces]
    return (any(r.get("defined") and (r.get("origin") or "").startswith("arch/") for r in recs)
            and any(r.get("defined") and not (r.get("origin") or "").startswith("arch/") for r in recs))


def _defined_anywhere(name: str, traces: Mapping[str, Mapping[str, Any]]) -> bool:
    return any((traces[c].get(name) or {}).get("defined") for c in traces)


def f1_instances(c_text: str, traces: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for inv in pasted_invocations(c_text):
        macros = sorted({n for n, _ in inv["names"] if overridable(n, traces)})
        if not macros:
            continue
        entity_args = sorted({inv["args"][i] for n, i in inv["names"] if not _defined_anywhere(n, traces)})
        if entity_args:
            out.append({"family": "F1", "kind": "pasted", "site": "%s(%s)" % (inv["macro"], ", ".join(inv["args"])),
                        "entities": entity_args, "macros": macros})
    for fn, body in _functions(c_text).items():
        used = sorted({t for t in re.findall(r"\b[A-Za-z_]\w*\b", body) if overridable(t, traces)})
        if used:
            out.append({"family": "F1", "kind": "direct", "site": fn, "entities": [fn], "macros": used})
    return out


def f2_instances(c_text: str, traces: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    uses = consumed(c_text)
    names = {n for c in traces for n, r in traces[c].items() if r.get("defined")}
    chains = {}

    def ch(n):
        if n not in chains:
            chains[n] = chain(n, traces)
        return chains[n]

    geometry = sorted(g for g in uses if g in names and g.endswith(GEOMETRY_SUFFIXES)
                      and any(arch_dependent(m, traces) for m in ch(g)))
    limits = sorted(n for n in names if ("MAX" in n or "LIMIT" in n) and n.endswith(GEOMETRY_SUFFIXES))
    functions = _functions(c_text)
    out = []
    for g in geometry:
        suffix = next(s for s in GEOMETRY_SUFFIXES if g.endswith(s))
        g_chain = set(ch(g))
        for lim in limits:
            if lim == g or not lim.endswith(suffix) or not (set(ch(lim)) & g_chain):
                continue
            # Macros the consumer uses whose chain reaches g count as uses of g for gating.
            reaching = {m for m in uses if m in names and g in ch(m)}
            gates = sorted(fn for fn, body in functions.items() if set(re.findall(r"\b[A-Za-z_]\w*\b", body)) & reaching)
            out.append({"family": "F2", "geometry": g, "limit": lim, "gates": gates})
    return out


MAX_ARGS = 8  # and/or arity bound of the v2 core


def _nary(op: str, args: list[dict[str, Any]]) -> dict[str, Any]:
    """``op`` over any number of arguments, nested so no node exceeds the core's arity bound."""
    if len(args) == 1:
        return args[0]
    while len(args) > MAX_ARGS:
        args = [_nary(op, args[i:i + MAX_ARGS]) for i in range(0, len(args), MAX_ARGS)]
    return {"op": op, "args": args}


def contract(instance: Mapping[str, Any]) -> dict[str, Any]:
    """The registered relation for one instance (scope always true)."""
    base = {"expressible": True, "strength": "necessary_only", "config_symbols": ["build_context"], "scope": {"symbol": "build_context"}}
    if instance["family"] == "F1":
        emits = [{"symbol": "emits_" + e} for e in instance["entities"]]
        provided = [{"symbol": "arch_provides_" + m} for m in instance["macros"]]
        rel = {"op": "or", "args": [{"op": "not", "args": [_nary("or", emits)]}, _nary("and", provided)]}
        return dict(base, reason="F1 " + instance["site"], relation=rel)
    le = {"op": "le", "args": [{"symbol": "value_" + instance["geometry"]}, {"symbol": "value_" + instance["limit"]}]}
    gates = [{"symbol": fn + "_returns_only_zero"} for fn in instance["gates"]]
    return dict(base, reason="F2 %s vs %s" % (instance["geometry"], instance["limit"]), relation=_nary("or", gates + [le]))


def queries(instance: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Fact queries the instance's contract needs, plus the build_context constant."""
    qs = [{"name": "build_context", "kind": "constant", "value": True}]
    if instance["family"] == "F1":
        qs += [{"name": "emits_" + e, "kind": "object_defines_token", "token": e} for e in instance["entities"]]
        qs += [{"name": "arch_provides_" + m, "kind": "macro_from_arch", "macro": m} for m in instance["macros"]]
    else:
        qs += [{"name": "value_" + m, "kind": "macro_value", "macro": m} for m in (instance["geometry"], instance["limit"])]
        qs += [{"name": fn + "_returns_only_zero", "kind": "returns_only_zero", "function": fn} for fn in instance["gates"]]
    return qs
