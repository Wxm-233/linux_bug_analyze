"""E1 candidate -> fact queries -> (optional model formalization) -> v2 contract evaluation.

Step 1 is mechanical: each provider/consumer reference becomes its enclosing top-level function, the
identifiers on the cited line, and any CONFIG_* named in the candidate text; these give named fact
queries with plain meanings (a value-blind vocabulary). Step 2 asks a model to express the candidate's
requirement only over that vocabulary in the v2 DSL; the program validates it and never repairs it.
Step 3 evaluates with the core; model-proposed requirement/authority claims stay ``insufficient`` until a
researcher reviews them (``reviewed=True``). No relation is inferred by the program.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from .contract_envelope import build_envelope, symbol_type, symbols_used, whole
from .contract_protocol import CLAIM_ROLES, ContractError
from .contract_protocol_v2 import evaluate_contract, validate_contract

C_WORDS = {"if", "else", "for", "while", "do", "return", "switch", "case", "break", "continue", "goto", "sizeof",
           "struct", "union", "enum", "static", "const", "volatile", "inline", "unsigned", "signed", "int", "long",
           "short", "char", "void", "bool", "true", "false", "NULL", "u8", "u16", "u32", "u64", "s8", "s16", "s32",
           "s64", "extern", "typeof", "default", "register", "auto", "restrict", "float", "double"}


def function_spans(text: str) -> list[tuple[int, int, str | None]]:
    """Top-level brace spans (first line, last line, identifier before the header's '(')."""
    out, depth, start, header = [], 0, None, None
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        code = re.sub(r"//.*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", "", line)
        if depth == 0 and "{" in code:
            window = " ".join(lines[max(0, n - 4):n]).split("{")[0]
            names = re.findall(r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:__\w+\s*)*$", window)
            start, header = n, (names[-1] if names else None)
        depth += code.count("{") - code.count("}")
        if depth == 0 and start is not None:
            out.append((start, n, header))
            start = None
    return out


def enclosing(spans: list[tuple[int, int, str | None]], line: int) -> str | None:
    hits = [h for s, e, h in spans if s <= line <= e and h]
    return hits[0] if hits else None


def identifiers(line: str) -> list[str]:
    code = re.sub(r"//.*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"", " ", line)
    seen = []
    for tok in re.findall(r"\b[A-Za-z_]\w*\b", code):
        if tok not in C_WORDS and len(tok) > 2 and tok not in seen:
            seen.append(tok)
    return seen


def build_queries(candidates: list[Mapping[str, Any]], sources: Mapping[str, str]) -> list[dict[str, Any]]:
    spans = {path: function_spans(text) for path, text in sources.items()}
    out = []
    for index, cand in enumerate(candidates):
        queries, vocab, functions = [], [], []

        def add(name, query, meaning):
            if name not in {q["name"] for q in queries}:
                queries.append(dict(query, name=name))
                vocab.append({"name": name, "kind": query["kind"], "meaning": meaning})

        add("build_context", {"kind": "constant", "value": True},
            "always true; use as the scope when the requirement applies to every build of this source")
        role_fn = {}
        for role in ("provider", "consumer"):
            ref = cand.get(role) or {}
            path, line = ref.get("file"), ref.get("line")
            if path not in sources or type(line) is not int:
                continue
            fn = enclosing(spans[path], line)
            if not fn:
                continue
            functions.append(fn)
            role_fn[role] = fn
            add(f"{role}_defined", {"kind": "defined", "function": fn},
                f"{role} function {fn} has its own symbol in the compiled object (false if inlined)")
            add(f"{role}_in_init", {"kind": "in_init", "function": fn},
                f"{role} function {fn} is placed in an init section (__init etc.), i.e. boot-time only")
            text_line = sources[path].splitlines()[line - 1] if 0 < line <= len(sources[path].splitlines()) else ""
            for ident in identifiers(text_line):
                if ident == fn:
                    continue
                key = re.sub(r"\W", "_", ident)
                add(f"{role}_may_ref_{key}", {"kind": "may_reference", "function": fn, "symbol": ident},
                    f"{fn} (or a caller it is inlined into) has a relocation to symbol {ident}")
                add(f"{role}_text_{key}", {"kind": "expansion_contains", "function": fn, "text": ident},
                    f"preprocessed body of {fn} contains the text {ident}")
                add(f"{role}_writes_{key}", {"kind": "writes", "function": fn, "object": ident},
                    f"{fn} syntactically assigns/increments variable or field {ident} (no alias analysis)")
                add(f"{role}_reads_{key}", {"kind": "reads", "function": fn, "object": ident},
                    f"{fn} syntactically reads variable or field {ident}")
                add(f"writers_count_{key}", {"kind": "writers_count", "object": ident},
                    f"number of functions in this source file that syntactically write {ident}")
                add(f"all_writers_in_init_{key}", {"kind": "all_writers_in_init", "object": ident},
                    f"every function in this source file that writes {ident} is in an init section")
                add(f"reader_outside_init_{key}", {"kind": "any_reader_outside_init", "object": ident},
                    f"some function in this source file that reads {ident} is not in an init section (may run after boot)")
        if "provider" in role_fn and "consumer" in role_fn and role_fn["provider"] != role_fn["consumer"]:
            p, c = role_fn["provider"], role_fn["consumer"]
            add("provider_reaches_consumer", {"kind": "reachable", "function": p, "callee": c},
                f"{p} calls {c} directly or transitively within this source file (callbacks/other files not visible)")
            add("consumer_reaches_provider", {"kind": "reachable", "function": c, "callee": p},
                f"{c} calls {p} directly or transitively within this source file (callbacks/other files not visible)")
        blob = " ".join(str(cand.get(k, "")) for k in ("requirement", "conditions", "risk"))
        for opt in dict.fromkeys(re.findall(r"\bCONFIG_[A-Z0-9_]+\b", blob)):
            add(opt.lower(), {"kind": "config", "option": opt, "absent_is_false": True},
                f"value of {opt} in this build configuration (false if unset)")
        out.append({"candidate": index, "functions": sorted(set(functions)), "queries": queries, "vocabulary": vocab})
    return out


def arch_needs(candidates: list[Mapping[str, Any]], sources: Mapping[str, str]) -> dict[str, Any]:
    """Macros, UAPI headers and CONFIG symbols a cross-architecture tree collection must cover."""
    # Architecture-overridable entry headers (seen under arch/*/include/uapi) come first: a consumer includes
    # those, and same-named facts keep the first header. Generic-only headers follow.
    arch_headers, generic_headers = set(), set()
    for path in sources:
        m = re.match(r"arch/[^/]+/include/uapi/(asm/.+\.h)$", path)
        if m:
            arch_headers.add(m.group(1))
        m = re.match(r"include/uapi/asm-generic/(.+\.h)$", path)
        if m:
            generic_headers.add("asm/" + m.group(1))
    headers = sorted(arch_headers) + sorted(generic_headers - arch_headers)
    macros, configs = set(), set()
    for cand in candidates:
        blob = " ".join(str(cand.get(k, "")) for k in ("interface", "requirement", "conditions", "risk"))
        for role in ("provider", "consumer"):
            ref = cand.get(role) or {}
            if ref.get("file") in sources and type(ref.get("line")) is int:
                lines = sources[ref["file"]].splitlines()
                if 0 < ref["line"] <= len(lines):
                    blob += " " + lines[ref["line"] - 1]
        configs |= set(re.findall(r"\bCONFIG_([A-Z0-9_]+)\b", blob))
        macros |= {t for t in re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", blob) if not t.startswith(("CONFIG_", "ARCH_"))}
    return {"headers": headers, "macros": sorted(macros), "config_symbols": sorted(configs)}


def build_arch_queries(candidates: list[Mapping[str, Any]], sources: Mapping[str, str], needs: Mapping[str, Any],
                       kconfig_deps: Mapping[str, list[str]], built_file: str | None = None) -> list[dict[str, Any]]:
    """Per-architecture fact vocabulary (same names for every architecture context)."""
    out = []
    for index, cand in enumerate(candidates):
        queries, vocab = [], []

        def add(name, query, meaning):
            if name not in {q["name"] for q in queries}:
                queries.append(dict(query, name=name))
                vocab.append({"name": name, "kind": query["kind"], "meaning": meaning})

        add("build_context", {"kind": "constant", "value": True}, "always true; scope for requirements that apply to every architecture")
        blob = " ".join(str(cand.get(k, "")) for k in ("interface", "requirement", "conditions", "risk"))
        for macro in needs["macros"]:
            if macro not in blob:
                continue
            for header in needs["headers"]:
                key = re.sub(r"\W", "_", header.replace("asm/", "").replace(".h", ""))
                add(f"defines_{macro}", {"kind": "uapi_defined", "header": header, "macro": macro},
                    f"this architecture's <{header}> include chain defines {macro} (user-space view, -dM final state)")
                add(f"value_{macro}", {"kind": "uapi_value", "header": header, "macro": macro},
                    f"integer value of {macro} from this architecture's <{header}>")
        for sym in needs["config_symbols"]:
            if "CONFIG_" + sym not in blob:
                continue
            for dep in kconfig_deps.get(sym, []):
                for arch_sym in re.findall(r"\b(ARCH_\w+|HAVE_\w+)\b", dep):
                    add(f"arch_selects_{arch_sym}", {"kind": "kconfig_selects", "symbol": arch_sym},
                        f"this architecture's Kconfig selects {arch_sym}, which CONFIG_{sym} depends on (so CONFIG_{sym} can be enabled only if true)")
            if built_file:
                add(f"config_{sym.lower()}", {"kind": "config", "option": "CONFIG_" + sym, "absent_is_false": True},
                    f"CONFIG_{sym} in the defconfig build attempted with it enabled (only architectures with a cross compiler)")
        if built_file:
            add("builds_ok", {"kind": "build_ok", "file": built_file},
                f"{built_file} compiles in this architecture's defconfig build (only architectures with a cross compiler)")
        out.append({"candidate": index, "queries": queries, "vocabulary": vocab})
    return out


RANGE_CAP = 80  # longest line range taken from a reference's "what" text


def _what_lines(what: str) -> list[int]:
    """Line numbers a reference's description cites in the same file: 第A-B及C、D行 / lines A-B."""
    out = []
    for span in re.findall(r"第([0-9、,，\-–~至及和与 ]+)行", what) + re.findall(r"\blines?\s+([0-9,\-– and]+)", what):
        for a, b in re.findall(r"(\d+)(?:\s*[-–~至]\s*(\d+))?", span):
            lo, hi = int(a), int(b or a)
            if lo <= hi <= lo + RANGE_CAP:
                out.extend(range(lo, hi + 1))
    return out


def _candidate_blob(cand: Mapping[str, Any], sources: Mapping[str, str]) -> tuple[str, list[str]]:
    """Candidate text plus the cited line and the line ranges its references' descriptions name."""
    blob = " ".join(str(cand.get(k, "")) for k in ("interface", "requirement", "conditions", "risk"))
    cited = []
    for role in ("provider", "consumer"):
        ref = cand.get(role) or {}
        if ref.get("file") in sources and type(ref.get("line")) is int:
            lines = sources[ref["file"]].splitlines()
            for n in dict.fromkeys([ref["line"]] + _what_lines(str(ref.get("what", "")))):
                if 0 < n <= len(lines):
                    cited.append(lines[n - 1])
    return blob + " " + " ".join(cited), cited


def _wildcards(blob: str, names: set[str]) -> set[str]:
    """Names matched by wildcard identifiers in the candidate text (topology_*_id)."""
    hits = set()
    for pat in set(re.findall(r"\b[A-Za-z_][\w*]*\*[\w*]*", blob)):
        rx = re.compile("^" + re.escape(pat).replace(r"\*", r"\w+") + "$")
        hits |= {n for n in names if rx.match(n)}
    return hits


def tu_needs(candidates: list[Mapping[str, Any]], sources: Mapping[str, str]) -> dict[str, Any]:
    """Macros to trace in the compilation unit: candidate/cited-line identifiers the sources use as macros."""
    macro_like = set()
    for text in sources.values():
        macro_like |= set(re.findall(r"^\s*#\s*(?:define|ifdef|ifndef|undef)\s+([A-Za-z_]\w*)", text, re.M))
        macro_like |= set(re.findall(r"\bdefined\s*\(?\s*([A-Za-z_]\w*)", text))
    macros, configs = set(), set()
    for cand in candidates:
        blob, _ = _candidate_blob(cand, sources)
        found = {t for t in re.findall(r"\b[A-Za-z_]\w*\b", blob) if t in macro_like} | _wildcards(blob, macro_like)
        macros |= {t for t in found if not t.startswith("CONFIG_")}
        configs |= set(re.findall(r"\bCONFIG_([A-Z0-9_]+)\b", blob))
    return {"macros": sorted(macros), "config_symbols": sorted(configs)}


def build_tu_queries(candidates: list[Mapping[str, Any]], sources: Mapping[str, str], needs: Mapping[str, Any],
                     built_file: str) -> list[dict[str, Any]]:
    """Per-build-context vocabulary over the compilation unit of ``built_file`` (same names in every context)."""
    out = []
    for index, cand in enumerate(candidates):
        queries, vocab = [], []

        def add(name, query, meaning):
            if name not in {q["name"] for q in queries}:
                queries.append(dict(query, name=name))
                vocab.append({"name": name, "kind": query["kind"], "meaning": meaning})

        add("build_context", {"kind": "constant", "value": True}, "always true; scope for requirements that apply to every build context")
        blob, cited = _candidate_blob(cand, sources)
        words = set(re.findall(r"\b[A-Za-z_]\w*\b", blob)) | _wildcards(blob, set(needs["macros"]))
        for macro in needs["macros"]:
            if macro not in words:
                continue
            add(f"defined_{macro}", {"kind": "macro_defined", "macro": macro},
                f"{macro} is defined at the end of {built_file}'s compilation unit (any source, including generic fallbacks)")
            add(f"arch_provides_{macro}", {"kind": "macro_from_arch", "macro": macro},
                f"the final definition of {macro} in that compilation unit comes from an arch/ header (not a generic fallback)")
        for line in cited:
            if line.lstrip().startswith("#"):
                continue  # directives name macros and headers, not object symbols
            for ident in identifiers(line):
                if ident.islower() and ident not in needs["macros"]:
                    add(f"emits_{ident}", {"kind": "object_defines_token", "token": ident},
                        f"the compiled {built_file} object defines a symbol named {ident} or containing it as an _-separated part (e.g. dev_attr_{ident})")
        for sym in needs["config_symbols"]:
            if "CONFIG_" + sym in blob:
                add(f"config_{sym.lower()}", {"kind": "config", "option": "CONFIG_" + sym, "absent_is_false": True},
                    f"CONFIG_{sym} in this build context's .config")
        add("builds_ok", {"kind": "build_ok", "file": built_file}, f"{built_file} compiles in this build context")
        out.append({"candidate": index, "queries": queries, "vocabulary": vocab})
    return out


ARCH_NOTE = """以下事实按每个架构分别求值（同一个事实名在不同架构有不同取值）；写出的scope与relation将对每个架构各判定一次。只能通过事实名引用架构差异，不要写架构名常量。
"""


BUILD_CONTEXT_NOTE = """以下事实按每个构建上下文（架构加配置）分别求值（同一个事实名在不同上下文有不同取值）；写出的scope与relation将对每个上下文各判定一次。只能通过事实名引用上下文差异，不要写架构名或配置名常量。
"""


FORMALIZE_HEADER = """你将把若干条候选“接口要求”改写为受限的形式关系。只能使用每个候选给出的事实名；事实值你看不到，也不要猜测。

形式语言（JSON表达式）：{"symbol": 名} | {"literal": 值} | {"op": 运算, "args": [...]}，运算限于 and/or/not/eq/ne/lt/le/gt/ge/min/max。
每个候选输出：{"candidate": 编号, "expressible": true/false, "reason": "一句话", "config_symbols": [作为适用条件的事实名], "scope": 表达式, "relation": 表达式}。
scope只能用config_symbols中的事实，且必须为布尔；relation必须为布尔且至少使用一个非config事实。若该要求无法只用给出的事实表达，expressible为false，scope与relation给null。
只输出一个JSON对象：{"formalizations": [...]}，不要输出其他文字。
"""


NECESSARY_NOTE = """另外允许“必要条件”形式化：若整条要求无法表达，但能用给出的事实写出该要求成立时必然成立的一个条件（违反它即说明要求被违反），可以给出该条件，并在该候选中加 "strength": "necessary_only"；完整表达时 "strength": "full"。不得写与要求无关或必然为真的条件；仍无法写出时 expressible 为 false。
"""


def formalization_prompt(candidates: list[Mapping[str, Any]], bridged: list[Mapping[str, Any]], types: Mapping[int, Mapping[str, str]],
                         mode: str = "full", per_arch: bool = False) -> str:
    note = BUILD_CONTEXT_NOTE if per_arch == "build" else ARCH_NOTE if per_arch else ""
    parts = [FORMALIZE_HEADER + (NECESSARY_NOTE if mode == "necessary" else "") + note]
    for cand, br in zip(candidates, bridged):
        parts.append(json.dumps({"candidate": br["candidate"],
                                 "requirement": cand.get("requirement"), "conditions": cand.get("conditions"),
                                 "facts": [dict(v, type=types.get(br["candidate"], {}).get(v["name"], "unavailable"))
                                           for v in br["vocabulary"]]}, ensure_ascii=False))
    return "\n\n".join(parts) + "\n"


def parse_formalizations(text: str) -> dict[int, dict[str, Any]]:
    start, end = text.find("{"), text.rfind("}")
    obj = json.loads(text[start:end + 1])
    return {int(f["candidate"]): f for f in obj["formalizations"]}


def evaluate_candidate(formal: Mapping[str, Any], facts: Mapping[str, Any], *, context: str, revision: str, basis: str,
                       documents: Mapping[str, Any], reviewed: bool, synthetic: bool = False) -> dict[str, Any]:
    """Build and judge one contract. Unreviewed model requirements stay insufficient by core rules.
    ``synthetic`` marks counterfactual control facts (basis 'synthetic', explicit core opt-in)."""
    if synthetic:
        basis = "synthetic"
    if not formal.get("expressible"):
        return {"status": "not_expressible", "reason": formal.get("reason")}
    scope, relation = formal.get("scope"), formal.get("relation")
    config = set(formal.get("config_symbols") or [])
    try:
        names = symbols_used(scope, relation)
    except (TypeError, AttributeError):
        return {"status": "invalid_formalization", "reason": "malformed expression"}
    missing = sorted(n for n in names if n not in facts)
    symbols = {n: {"type": symbol_type(facts[n]) if n in facts else "bool", "role": "configuration" if n in config else "observation"}
               for n in sorted(names)}
    origins = {k: ("researcher_authored" if reviewed else "model_proposal") for k in ("scope", "relation", "symbols", "required_claims", "authority_kind")}
    probe = {"schema": "architecture_contract_v2", "id": "probe", "revision": revision, "authority_kind": "consumer_inferred",
             "sufficient_for_correctness": False, "field_origins": origins, "symbols": symbols,
             "required_claims": {r: "review." + r for r in CLAIM_ROLES}, "scope": scope, "relation": relation}
    try:
        validate_contract(probe)
    except ContractError as exc:
        return {"status": "invalid_formalization", "reason": str(exc)}
    if missing:
        return {"status": "facts_unavailable", "missing": missing}
    origin = "researcher_review" if reviewed else "model_proposal"
    roles = {r: {"statement": "Candidate requirement formalized over generated facts" + ("; reviewed." if reviewed else "; NOT reviewed."),
                 "references": whole(documents, "evidence"), "origin": origin if r in ("authority", "consumer_requirement") else "researcher_review"}
             for r in CLAIM_ROLES}
    spec = {"schema": "architecture_contract_v2", "contract_id": "bridge." + context, "revision": revision, "basis": basis,
            "context_id": context, "object_id": context + ".object", "sample_event": context + ".sample",
            "deadline_event": context + ".unobserved_consumer", "authority_kind": "consumer_inferred", "field_origins": origins,
            "symbols": symbols, "scope": scope, "relation": relation, "documents": documents, "role_claims": roles,
            "observation_claim": {"statement": "Generic kernel fact bundle answers.", "references": whole(documents, "evidence")},
            "facts": {n: {"value": facts[n], "statement": "Counterfactual control value." if synthetic else "Answered from the fact bundle.",
                          "references": whole(documents, "evidence"), **({"origin": "synthetic_assumption"} if synthetic else {})} for n in symbols}}
    item = build_envelope(spec)
    result = evaluate_contract(item["contract"], item["ledger"], item["record"], allow_synthetic=synthetic)
    return {"status": "evaluated", "reviewed": reviewed, **{k: result[k] for k in ("applicability", "relation_at_observation", "reasons")}}
