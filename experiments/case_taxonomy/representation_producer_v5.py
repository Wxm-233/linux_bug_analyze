"""Producer v5: distinguish endian values from pointer/array objects.

Wrap frozen v4; no old parser or result is changed. This is bounded declaration
and lvalue evidence, not a C compiler, alias analysis, or consumer/hardware proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import representation_producer_v4 as v4

v3 = v4.v3
VERSION = "representation-producer-v5.0"
IDENT = v3.IDENT
BASE = rf"__(?:aligned_)?(?:le|be)(?:16|32|64)|(?:struct|union)\s+{IDENT}|u(?:8|16|32|64)"
DECL = re.compile(rf"\b(?P<type>{BASE})\s+(?P<tail>[^;{{}}]+)\s*;", re.S)
SIMPLE_TAIL = re.compile(rf"(?P<stars>(?:\*\s*)*)(?P<name>{IDENT})(?P<arrays>(?:\s*\[[^\[\];]*\])*)\s*$", re.S)
COMPONENT = rf"{IDENT}(?:\s*\[[^\[\];]+\])*"
PATH = rf"{COMPONENT}(?:\s*(?:\.|->)\s*{COMPONENT}){{1,5}}"
SITE = re.compile(rf"(?<![\w.>])(?P<lhs>(?:(?:\*\s*)+\(\s*{PATH}\s*\)|(?:\*\s*)*{PATH}))\s*(?P<op>\|=|=)(?!=)\s*(?P<rhs>[^;]+);", re.S)
PART = re.compile(rf"(?P<name>{IDENT})(?P<indices>(?:\s*\[[^\[\];]+\])*)")


def conditional_lines(clean: str, *, header_file: bool = False) -> list[bool]:
    """Refuse configuration conditions; canonical outer header guard is assumed.

    This is not preprocessing. The guard exemption is only an inventory-reading
    convention and does not assert the real compilation included this header.
    """
    guard = (re.match(rf"\s*#\s*ifndef\s+({IDENT})\s*\n\s*#\s*define\s+\1\s*\n", clean)
             if header_file and re.search(r"#\s*endif\s*$", clean) else None)
    guard_line = v3.line_number(clean, clean.find("#")) if guard else None
    stack, guarded_else, result = [], False, []
    for number, line in enumerate(clean.splitlines(), 1):
        result.append(any(stack))
        if re.match(r"\s*#\s*(?:if|ifdef|ifndef)\b", line):
            stack.append(number != guard_line)
        elif re.match(r"\s*#\s*(?:else|elif)\b", line):
            if len(stack) == 1 and not stack[-1]:
                guarded_else = True
            if stack:
                stack[-1] = True
        elif re.match(r"\s*#\s*endif\b", line) and stack:
            stack.pop()
    if guarded_else:
        # An outer guard with alternatives is not the accepted header idiom.
        return [True] * len(result)
    return result


def declaration_shapes(files: dict[str, str]) -> dict[str, list[dict]]:
    """Only direct, singly named declarators; opaque forms retain a refusal."""
    layouts: dict[str, list[dict]] = {}
    for path, source in files.items():
        clean = v3.mask_comments_and_literals(source)
        conditioned = conditional_lines(clean, header_file=path.endswith(".h"))

        def parse(key: str, opening: int, closing: int) -> None:
            body = clean[opening + 1:closing]
            depth, direct = 0, []
            for char in body:
                direct.append(depth == 0)
                depth += (char == "{") - (char == "}")
            members = []
            for match in DECL.finditer(body):
                if not direct[match.start()]:
                    continue
                tail = match.group("tail").strip()
                simple = SIMPLE_TAIL.fullmatch(tail)
                common = {"type": " ".join(match.group("type").split()),
                          "file": path, "line": v3.line_number(source, opening + 1 + match.start()),
                          "declaration_text": " ".join(source[opening + 1 + match.start():opening + 1 + match.end()].split())}
                first_line = common["line"]
                last_line = v3.line_number(source, opening + 1 + match.end())
                conditional = any(conditioned[first_line - 1:last_line])
                if simple:
                    arrays = re.findall(r"\[([^\[\]]*)\]", simple.group("arrays"))
                    members.append({**common, "name": simple.group("name"),
                        "layers": ["array"] * len(arrays) + ["pointer"] * simple.group("stars").count("*"),
                        "array_bounds": arrays, "status": "insufficient" if conditional else "proven",
                        **({"reason": "member declaration is under an unresolved preprocessing condition"} if conditional else {})})
                else:
                    # Names in a complex declarator are merely lookup leads.
                    # Never infer pointer/array order from these names.
                    names = set(re.findall(IDENT, tail)) - {"const", "volatile", "restrict"}
                    for name in names:
                        members.append({**common, "name": name, "layers": None,
                            "status": "insufficient", "reason": "complex or multiple member declarator is outside the bounded shape grammar"})
            for anon in v3.ANON_OPEN.finditer(body):
                if not direct[anon.start()]:
                    continue
                child_open = opening + 1 + anon.end() - 1
                child_close = v3.closing_delimiter(clean, child_open, "{", "}")
                if child_close is None or child_close >= closing:
                    continue
                suffix = re.match(rf"\s*({IDENT})\s*;", clean[child_close + 1:closing])
                if suffix:
                    name = suffix.group(1)
                    child_key = f"@{key}.{name}"
                    parse(child_key, child_open, child_close)
                    conditional = conditioned[v3.line_number(source, child_open) - 1]
                    members.append({"name": name, "type": child_key, "layers": [],
                        "status": "insufficient" if conditional else "proven", "file": path,
                        **({"reason": "member declaration is under an unresolved preprocessing condition"} if conditional else {}),
                        "line": v3.line_number(source, child_open), "declaration_text": "named inline aggregate"})
            layouts.setdefault(key, []).append({"file": path, "members": members})

        for match in v3.TYPE_OPEN.finditer(clean):
            opening = match.end() - 1
            closing = v3.closing_delimiter(clean, opening, "{", "}")
            if closing is not None:
                parse(f"{match.group(1)} {match.group(2)}", opening, closing)
    return layouts


def lvalue_sites(source: str) -> list[dict]:
    clean = v3.mask_comments_and_literals(source)
    result = []
    for function in v3.FUNCTION_OPEN.finditer(clean):
        if function.group(1) in v3.CONTROL:
            continue
        opening = function.end() - 1
        closing = v3.closing_delimiter(clean, opening, "{", "}")
        if closing is None:
            continue
        for match in SITE.finditer(clean, opening + 1, closing):
            lhs = match.group("lhs").strip()
            stars = re.match(r"(?:\*\s*)*", lhs).group().count("*")
            path = re.sub(r"^(?:\*\s*)+", "", lhs).strip()
            if path.startswith("(") and path.endswith(")"):
                path = path[1:-1].strip()
            parts = list(PART.finditer(path))
            selectors = re.findall(r"\.|->", path)
            if len(parts) != len(selectors) + 1:
                continue
            line = v3.line_number(source, match.start())
            prefix = function.group(2) + ";" + clean[opening + 1:match.start()]
            roots = [entry for entry in v3.OBJECT_DECL.finditer(prefix)
                     if entry.group("name") == parts[0].group("name")]
            root_evidence = None
            if len(roots) == 1:
                declaration_at = (function.start(2) + roots[0].start()
                    if roots[0].start() < len(function.group(2)) else
                    opening + 1 + roots[0].start() - len(function.group(2)) - 1)
                root_evidence = {"line": v3.line_number(source, declaration_at),
                    "declaration_text": " ".join(roots[0].group().split()),
                    "type": " ".join(roots[0].group("type").split()),
                    "pointer": bool(roots[0].group("pointer")),
                    "note": "bounded declaration before this write; not full C scope or path proof"}
            result.append({"function": function.group(1), "line": line,
                "object": parts[0].group("name"), "field": parts[-1].group("name"),
                "lhs": " ".join(source[match.start("lhs"):match.end("lhs")].split()),
                "path": path, "parts": [(p.group("name"), p.group("indices").count("[")) for p in parts],
                "selectors": selectors, "dereferences": stars,
                "rhs": " ".join(source[match.start("rhs"):match.end("rhs")].split()),
                "op": match.group("op"), "begin": match.start("lhs"), "end": match.end("lhs"),
                "struct": " ".join(roots[0].group("type").split()) if len(roots) == 1 else None,
                "root_pointer": bool(roots[0].group("pointer")) if len(roots) == 1 else None,
                "root_declaration": root_evidence})
    return result


def resolve_shape(site: dict, layouts: dict) -> dict:
    proof = {"lvalue": site["lhs"], "declarations": [], "status": "insufficient",
             "root_declaration_before_write": site["root_declaration"]}
    key = site["struct"]
    if key is None:
        proof["reason"] = "root object declaration is missing or ambiguous"
        return proof
    root_layers = ["pointer"] if site["root_pointer"] else []
    # Root arrays and compound root declarators are not established by v4's
    # single object grammar; indices on a root are deliberately not promoted.
    if site["parts"][0][1]:
        proof["reason"] = "root object array/indirection shape not established"
        return proof
    for index, selector in enumerate(site["selectors"]):
        if selector == "->":
            if root_layers != ["pointer"]:
                proof["reason"] = "arrow does not have a proven single pointer to an aggregate"
                return proof
            root_layers = []
        elif root_layers:
            proof["reason"] = "dot access has unresolved pointer/array layers"
            return proof
        definitions = layouts.get(key, [])
        if len(definitions) != 1:
            proof["reason"] = "aggregate declaration is missing or ambiguous"
            return proof
        name, subscripts = site["parts"][index + 1]
        members = [member for member in definitions[0]["members"] if member["name"] == name]
        if len(members) != 1:
            proof["reason"] = "member declaration is missing or ambiguous"
            return proof
        member = members[0]
        proof["declarations"].append(member)
        if member["status"] != "proven":
            proof["reason"] = member["reason"]
            return proof
        root_layers = list(member["layers"])
        for _ in range(subscripts):
            if not root_layers:
                proof["reason"] = "subscript has no proven pointer/array layer"
                return proof
            root_layers.pop(0)
        key = member["type"]
    for _ in range(site["dereferences"]):
        if not root_layers or root_layers[0] != "pointer":
            proof["reason"] = "explicit dereference has no proven pointer layer"
            return proof
        root_layers.pop(0)
    proof.update({"status": "proven", "remaining_layers": root_layers,
                  "element_type": key, "consumed_explicit_dereferences": site["dereferences"]})
    if not root_layers:
        proof["target_kind"] = "scalar_value"
    elif root_layers[0] == "pointer":
        proof["target_kind"] = "pointer_object"
    else:
        proof["target_kind"] = "array_object"
    return proof


def analyze_text(source: str, source_path: str = "<synthetic>",
                 declaration_files: dict[str, str] | None = None) -> dict:
    files = dict(declaration_files or {source_path: source})
    files[source_path] = source
    layouts, sites = declaration_shapes(files), lvalue_sites(source)
    # Mask only parentheses/stars around an explicitly dereferenced member path.
    # Offsets/newlines and RHS remain unchanged; declaration depth is verified
    # against the original lvalue before retaining any local v4 verdict.
    normalized = list(source)
    for site in sites:
        if site["dereferences"] and "(" in site["lhs"]:
            for position in range(site["begin"], site["end"]):
                if normalized[position] in "*()":
                    normalized[position] = " "
    report = v4.analyze_text("".join(normalized), source_path, files)
    report["v4_counts_before_shape_review"] = dict(report["counts"])
    findings, filtered, seen = [], [], set()
    for item in report["findings"]:
        matches = [site for site in sites if (site["line"], site["object"], site["field"], site["function"])
                   == (item["line"], item["object"], item["field"], item["function"]) and site["rhs"] == item["rhs"]]
        item["v4_local_status"] = item["status"]
        if len(matches) != 1:
            item["status"], item["reason"] = "insufficient", "original lvalue/declaration shape cannot be uniquely established"
            item["proposed_check"] = None
            findings.append(item)
            continue
        site = matches[0]
        seen.add((site["begin"], site["end"], site["function"]))
        shape = resolve_shape(site, layouts)
        item["lvalue_shape_proof"] = shape
        item["original_lvalue"] = site["lhs"]
        item["original_source_line"] = source.splitlines()[site["line"] - 1].strip()
        if shape["status"] != "proven":
            item["status"], item["reason"] = "insufficient", shape["reason"]
        elif shape["target_kind"] == "pointer_object":
            item["status"], item["reason"] = "filtered_pointer_object", "assignment changes the pointer object, not its endian-typed pointed-to value"
            item["proposed_check"] = None
            filtered.append(item)
            continue
        elif shape["target_kind"] == "array_object":
            item["status"], item["reason"] = "insufficient", "whole array is not a scalar write target; declaration/assignment validity requires review"
        elif shape["element_type"].replace("__aligned_", "__") != item["destination_type"].replace("__aligned_", "__"):
            item["status"], item["reason"] = "insufficient", "resolved scalar element type differs from v4 target"
        if item["status"] == "insufficient":
            item["proposed_check"] = None
        findings.append(item)
    # Keep unsupported complex/member-layer sites visible rather than reporting
    # zero sites as normal. New scalar syntax never creates a v5 candidate.
    for site in sites:
        if (site["begin"], site["end"], site["function"]) in seen:
            continue
        shape = resolve_shape(site, layouts)
        if not shape["declarations"]:
            continue
        last = shape["declarations"][-1]
        if not re.fullmatch(r"__(?:aligned_)?(?:le|be)(?:16|32|64)", last["type"]):
            continue
        item = {"status": "insufficient", "reason": shape.get("reason", "scalar syntax not established by frozen v4"),
            "function": site["function"], "line": site["line"], "source_file": source_path,
            "object": site["object"], "field": site["field"], "struct": site["struct"],
            "rhs": site["rhs"], "destination_type": last["type"], "original_lvalue": site["lhs"],
            "original_source_line": source.splitlines()[site["line"] - 1].strip(),
            "lvalue_shape_proof": shape, "declaration": shape["declarations"], "proposed_check": None}
        if shape["status"] == "proven" and shape["target_kind"] == "pointer_object":
            item["status"], item["reason"] = "filtered_pointer_object", "assignment changes the pointer object, not its endian-typed pointed-to value"
            filtered.append(item)
        else:
            findings.append(item)
    counts = Counter(item["status"] for item in findings)
    report["findings"] = sorted(findings, key=lambda item: (item["line"], item["field"]))
    report["counts"] = {status: counts[status] for status in ("candidate", "normal", "insufficient")}
    report["filtered_pointer_sites"] = sorted(filtered, key=lambda item: (item["line"], item["field"]))
    report["filtered_pointer_count"] = len(filtered)
    report["source_sha256"] = v3.sha256(source)
    report["rule_version"] = VERSION
    report["scope"] = (report["scope"] + " v5 retains original declaration/lvalue depth; pointer-object writes are separately filtered, "
        "array objects and unsupported compound/root layers remain insufficient. Indexing or explicit dereference consumes only a proven layer. "
        "Conditional member declarations are refused; canonical outer #ifndef/#define header guards are inventory assumptions only, "
        "not actual compilation/include-order proof. A scalar normal verdict remains local; no buffer consumer, bounds, pointer validity, or hardware proof is added.")
    return report


def analyze_revision(linux_dir: Path, revision: str, source_path: str) -> dict:
    # Reuse v4's bounded include inventory, then read exactly that inventory.
    base = v4.analyze_revision(linux_dir, revision, source_path)
    files = {item["path"]: v3.git_file(linux_dir, revision, item["path"]) for item in base["files_read"]}
    if any(value is None for value in files.values()):
        raise FileNotFoundError("an inventoried source disappeared")
    report = analyze_text(files[source_path], source_path, files)
    report.update({"revision": revision, "files_read": base["files_read"], "include_notes": base["include_notes"]})
    report["implementation_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in
        (Path(__file__), Path(v4.__file__), Path(v3.__file__), Path(__file__).with_name("endian_consumer_single_revision.py"))}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze_revision(args.linux_dir, args.revision, args.source)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
