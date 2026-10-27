"""Find bounded producer-side representation review leads in one Git revision.

Version 2 adds array/nested member writes and 32-bit alias stores over a
byte-plus-three-byte descriptor slot. A pointer parameter is only an interface
lead; none of these syntactic leads proves a device contract or a defect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from endian_consumer_single_revision import (
    FUNCTION_OPEN, QUOTED_INCLUDE, STRUCT_OPEN, closing_delimiter, git_file,
    line_number, local_include_path, mask_comments_and_literals, source_tree,
)


IDENT = r"[A-Za-z_]\w*"
ENDIAN_FIELD = re.compile(rf"\b__(le|be)(16|32|64)\s+({IDENT})\s*;")
STRUCT_VARIABLE = re.compile(rf"\bstruct\s+({IDENT})\s+(\*\s*)?({IDENT})\b")
INITIALIZER = re.compile(rf"\bstruct\s+({IDENT})\s+({IDENT})\s*=\s*\{{")
MEMBER_ASSIGNMENT = re.compile(
    rf"\b({IDENT})\s*(?:\.|->)\s*({IDENT})\s*=(?!=)\s*([^;]*);", re.S
)
PARAM_TYPE = re.compile(
    rf"\b(__le(?:16|32|64)|__be(?:16|32|64)|u(?:16|32|64)|"
    rf"s(?:16|32|64)|unsigned\s+int)\s+(\*\s*)?({IDENT})\b"
)
CONTROL = {"if", "for", "while", "switch", "sizeof"}


def sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def declared_fields(source: str, source_path: str) -> dict[tuple[str, str], list[dict]]:
    """Only direct, scalar, endian-typed members declared in one source file."""
    clean = mask_comments_and_literals(source)
    result: dict[tuple[str, str], list[dict]] = {}
    for match in STRUCT_OPEN.finditer(clean):
        opening = match.end() - 1
        closing = closing_delimiter(clean, opening, "{", "}")
        if closing is None:
            continue
        body = clean[opening + 1:closing]
        depth = 1
        direct = []
        for char in body:
            direct.append(depth == 1)
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
        for field in ENDIAN_FIELD.finditer(body):
            if not direct[field.start()]:
                continue
            kind, bits, name = field.groups()
            result.setdefault((match.group(1), name), []).append({
                "type": f"__{kind}{bits}",
                "file": source_path,
                "line": line_number(source, opening + 1 + field.start()),
            })
    return result


def parameter_types(params: str) -> dict[str, str]:
    result = {}
    for match in PARAM_TYPE.finditer(params):
        if match.group(2):
            continue  # Pointer target value is not established by its name.
        result[match.group(3)] = " ".join(match.group(1).split())
    return result


def expression_type(expr: str, scalar_types: dict[str, str],
                    objects: dict[str, str], fields: dict) -> str | None:
    expr = expr.strip()
    if re.fullmatch(IDENT, expr):
        return scalar_types.get(expr)
    member = re.fullmatch(rf"({IDENT})\s*(?:\.|->)\s*({IDENT})", expr)
    if member and member.group(1) in objects:
        declaration = fields.get((objects[member.group(1)], member.group(2)), [])
        if len(declaration) == 1:
            return declaration[0]["type"]
    return None


def boundary_call(clean: str, source: str, begin: int, end: int,
                  object_name: str, pointer: bool) -> list[dict]:
    """Find later calls that directly pass this object, within one function."""
    def arguments_at_top_level(args: str) -> list[str]:
        parts = []
        depth = 0
        start = 0
        for index, char in enumerate(args):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append(args[start:index].strip())
                start = index + 1
        parts.append(args[start:].strip())
        return parts

    evidence = []
    remaining = clean[begin:end]
    for call in re.finditer(rf"\b({IDENT})\s*\(", remaining):
        name = call.group(1)
        if name in CONTROL:
            continue
        open_at = begin + call.end() - 1
        close_at = closing_delimiter(clean, open_at, "(", ")")
        if close_at is None or close_at > end:
            continue
        args = clean[open_at + 1:close_at]
        passed = (rf"&\s*{re.escape(object_name)}" if not pointer
                  else re.escape(object_name))
        if not any(re.fullmatch(passed, arg) for arg in arguments_at_top_level(args)):
            continue
        evidence.append({
            "callee": name,
            "line": line_number(source, begin + call.start()),
            "passes_object": source[open_at + 1:close_at].strip(),
        })
    return evidence


def classify(rhs: str, target: str, scalar_types: dict[str, str],
             objects: dict[str, str], fields: dict,
             interface: list[dict]) -> tuple[str, str, str | None]:
    rhs = rhs.strip()
    matched = re.fullmatch(r"__(le|be)(16|32|64)", target)
    assert matched is not None
    kind, bits = matched.groups()
    conversion = re.fullmatch(rf"cpu_to_{kind}{bits}\s*\(\s*({IDENT})\s*\)", rhs)
    native = {f"u{bits}", f"s{bits}"}
    if bits == "32":
        native.add("unsigned int")
    if conversion:
        input_type = scalar_types.get(conversion.group(1))
        if input_type in native:
            return ("normal", "host-typed scalar explicitly converted to the declared "
                    "representation", input_type)
        return ("insufficient", "conversion input is not proven host-typed in "
                "this function", input_type)
    if rhs == "0":
        return "normal", "zero has identical representation in either byte order", None
    source_type = expression_type(rhs, scalar_types, objects, fields)
    if source_type == target:
        return "normal", "copy from the same endian-typed representation", source_type
    if source_type in native:
        if interface:
            return ("candidate", "host-typed value directly assigned to an endian-typed "
                    "field before passing the object to a call", source_type)
        return ("insufficient", "host-typed direct assignment, but no later direct "
                "object-passing call found in this function", source_type)
    if source_type is not None:
        return "insufficient", "source representation differs or width is not established", source_type
    return "insufficient", "RHS type or transformation cannot be established", None


def analyze_text_v1(source: str, source_path: str = "<synthetic>",
                    declaration_files: dict[str, str] | None = None) -> dict:
    clean = mask_comments_and_literals(source)
    fields: dict[tuple[str, str], list[dict]] = {}
    for path, contents in (declaration_files or {source_path: source}).items():
        for key, values in declared_fields(contents, path).items():
            fields.setdefault(key, []).extend(values)
    findings = []
    for function in FUNCTION_OPEN.finditer(clean):
        name = function.group(1)
        if name in CONTROL:
            continue
        opening = function.end() - 1
        closing = closing_delimiter(clean, opening, "{", "}")
        if closing is None:
            continue
        body = clean[opening + 1:closing]
        scalars = parameter_types(function.group(2))
        objects: dict[str, str] = {}
        pointer_objects: set[str] = set()
        for declaration in STRUCT_VARIABLE.finditer(function.group(2) + ";" + body):
            struct, star, variable = declaration.groups()
            objects[variable] = struct
            if star:
                pointer_objects.add(variable)
        sites: list[tuple[int, int, str, str, str, str]] = []

        for initializer in INITIALIZER.finditer(body):
            struct, variable = initializer.groups()
            start = opening + 1 + initializer.end() - 1
            finish = closing_delimiter(clean, start, "{", "}")
            if finish is None or not re.match(r"\s*;", clean[finish + 1:closing]):
                continue
            objects[variable] = struct
            initialized = clean[start + 1:finish]
            # Supported initializer grammar: direct `.member = value` entries.
            for assignment in re.finditer(rf"\.\s*({IDENT})\s*=(?!=)\s*([^,{{}}]+)\s*(?:,|$)", initialized):
                rhs = source[start + 1 + assignment.start(2):start + 1 + assignment.end(2)]
                sites.append((start + 1 + assignment.start(), finish, variable,
                              assignment.group(1), rhs, "designated_initializer"))

        for assignment in MEMBER_ASSIGNMENT.finditer(body):
            variable, field, _ = assignment.groups()
            if variable not in objects:
                continue
            at = opening + 1 + assignment.start()
            rhs = source[opening + 1 + assignment.start(3):opening + 1 + assignment.end(3)]
            sites.append((at, opening + 1 + assignment.end(), variable,
                          field, rhs, "member_assignment"))

        for at, after, variable, field, rhs, assignment_kind in sites:
            declaration = fields.get((objects[variable], field), [])
            if not declaration:
                continue
            if len(declaration) != 1:
                status, reason, source_type = ("insufficient", "multiple field declarations",
                                               None)
                interface = []
            else:
                interface = boundary_call(clean, source, after, closing, variable,
                                          variable in pointer_objects)
                status, reason, source_type = classify(
                    rhs, declaration[0]["type"], scalars, objects, fields, interface
                )
            findings.append({
                "status": status, "reason": reason,
                "function": name, "assignment_kind": assignment_kind,
                "source_file": source_path, "line": line_number(source, at),
                "object": variable, "struct": objects[variable], "field": field,
                "destination_type": declaration[0]["type"],
                "rhs": " ".join(rhs.split()), "source_type": source_type,
                "declaration": declaration, "interface_evidence": interface,
            })
    counts = Counter(item["status"] for item in findings)
    return {
        "source_file": source_path, "source_sha256": sha256(source),
        "findings": sorted(findings, key=lambda item: (item["line"], item["field"])),
        "counts": {status: counts[status]
                   for status in ("candidate", "normal", "insufficient")},
        "scope": ("Direct scalar assignments to __le*/__be* fields declared in "
                  "this C file or quoted includes up to two edges. Candidate "
                  "requires a host-typed scalar "
                  "and a later object-passing call; it is a review lead, not a "
                  "defect verdict. Normal applies only to a local assignment."),
    }


TYPE_OPEN = re.compile(rf"\b(struct|union)\s+({IDENT})\s*\{{")
FIELD_DECL = re.compile(
    rf"\b(?P<type>__(?:le|be)(?:16|32|64)|u(?:8|16|32|64)|"
    rf"s(?:8|16|32|64)|(?:struct|union)\s+{IDENT})"
    rf"\s+(?P<pointer>\*\s*)?(?P<name>{IDENT})"
    rf"(?:\s*\[\s*(?P<count>\d+)\s*\])?\s*;"
)
ANON_OPEN = re.compile(r"\b(?:struct|union)\s*\{")
PATH_ASSIGNMENT = re.compile(
    rf"(?<!\w)(?P<path>{IDENT}(?:\s*\[[^\[\];]+\])?"
    rf"(?:\s*(?:\.|->)\s*{IDENT}(?:\s*\[[^\[\];]+\])?){{1,5}})"
    r"\s*=(?!=)\s*(?P<rhs>[^;]+);", re.S,
)
WIDE_ALIAS = re.compile(
    rf"\*\s*\(\s*(?P<cast>u32|__le32|__be32)\s*\*\s*\)\s*&\s*"
    rf"(?P<path>{IDENT}(?:\s*\[[^\[\];]+\])?"
    rf"(?:\s*(?:\.|->)\s*{IDENT}(?:\s*\[[^\[\];]+\])?){{1,5}})"
    r"\s*=(?!=)\s*(?P<rhs>[^;]+);", re.S,
)
HOST_DECL = re.compile(
    rf"\b(?P<type>__(?:le|be)(?:16|32|64)|u(?:8|16|32|64)|"
    rf"s(?:8|16|32|64)|unsigned\s+int|dma_addr_t|size_t)"
    rf"\s+(?P<name>{IDENT})\b"
)
OBJECT_DECL = re.compile(
    rf"\b(?P<type>(?:struct|union)\s+{IDENT})\s+"
    rf"(?P<pointer>\*\s*)?(?P<name>{IDENT})\b"
)


def type_layouts(files: dict[str, str]) -> dict[str, list[dict]]:
    """Read only simple declared member order; ambiguous definitions stay ambiguous."""
    layouts: dict[str, list[dict]] = {}
    for path, contents in files.items():
        clean = mask_comments_and_literals(contents)

        def parse_body(key: str, opening: int, closing: int) -> None:
            body = clean[opening + 1:closing]
            depth = 0
            direct = []
            for char in body:
                direct.append(depth == 0)
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
            members = []
            for field in FIELD_DECL.finditer(body):
                if not direct[field.start()]:
                    continue
                members.append({
                    "name": field.group("name"),
                    "type": " ".join(field.group("type").split()),
                    "count": int(field.group("count") or "1"),
                    "pointer": bool(field.group("pointer")),
                    "file": path,
                    "line": line_number(contents, opening + 1 + field.start()),
                    "offset": field.start(),
                })
            for anon in ANON_OPEN.finditer(body):
                if not direct[anon.start()]:
                    continue
                child_open = opening + 1 + anon.end() - 1
                child_close = closing_delimiter(clean, child_open, "{", "}")
                if child_close is None or child_close >= closing:
                    continue
                suffix = re.match(rf"\s*({IDENT})\s*;", clean[child_close + 1:closing])
                if suffix is None:
                    continue
                member_name = suffix.group(1)
                child_key = f"@{key}.{member_name}"
                parse_body(child_key, child_open, child_close)
                members.append({
                    "name": member_name, "type": child_key, "count": 1,
                    "pointer": False, "file": path,
                    "line": line_number(contents, child_open),
                    "offset": anon.start(),
                })
            layouts.setdefault(key, []).append({
                "file": path, "members": sorted(members, key=lambda item: item["offset"]),
            })

        for found in TYPE_OPEN.finditer(clean):
            opening = found.end() - 1
            closing = closing_delimiter(clean, opening, "{", "}")
            if closing is not None:
                parse_body(f"{found.group(1)} {found.group(2)}", opening, closing)
    return layouts


def path_parts(path: str) -> tuple[str, list[str]]:
    root = re.match(IDENT, path)
    assert root is not None
    return root.group(), re.findall(rf"(?:\.|->)\s*({IDENT})", path)


def resolved_member(path: str, roots: dict[str, str], layouts: dict
                    ) -> tuple[dict, list[dict], int] | None:
    root, parts = path_parts(path)
    key = roots.get(root)
    if key is None:
        return None
    for index, part in enumerate(parts):
        definitions = layouts.get(key, [])
        if len(definitions) != 1:
            return None
        members = definitions[0]["members"]
        matches = [(position, item) for position, item in enumerate(members)
                   if item["name"] == part]
        if len(matches) != 1:
            return None
        position, member = matches[0]
        if index == len(parts) - 1:
            return member, members, position
        key = member["type"]
    return None


def rhs_type(rhs: str, scalars: dict[str, str]) -> str | None:
    rhs = rhs.strip()
    if re.fullmatch(IDENT, rhs):
        return scalars.get(rhs)
    explicit_cast = re.fullmatch(
        r"\(\s*(u8|u16|u32|s8|s16|s32)\s*\)\s*\(.*\)", rhs, re.S)
    if explicit_cast:
        return explicit_cast.group(1)
    half = re.fullmatch(rf"(?:upper|lower)_32_bits\s*\(\s*({IDENT})\s*\)", rhs)
    if half and scalars.get(half.group(1)) in {
        "u32", "u64", "s32", "s64", "dma_addr_t", "size_t", "unsigned int",
    }:
        return "u32"
    return None


def extended_status(rhs: str, target: str, scalars: dict[str, str],
                    interface: list[dict]) -> tuple[str, str, str | None]:
    rhs = rhs.strip()
    if rhs == "0":
        return "normal", "zero is byte-order invariant at this site", None
    source_type = rhs_type(rhs, scalars)
    if source_type == target:
        return "normal", "same representation type at this site", source_type
    kind_bits = re.fullmatch(r"__(le|be)(16|32|64)", target)
    assert kind_bits is not None
    kind, bits = kind_bits.groups()
    conversion = re.fullmatch(rf"cpu_to_{kind}{bits}\s*\((.*)\)", rhs, re.S)
    host = {f"u{bits}", f"s{bits}"}
    if bits == "32":
        host.add("unsigned int")
    conversion_source = rhs_type(conversion.group(1), scalars) if conversion else None
    if conversion_source in host:
        return ("normal", "host scalar explicitly converted at this site",
                conversion_source)
    if conversion:
        return "insufficient", "conversion input type not established", source_type
    if source_type in host:
        if interface:
            return ("candidate", "host value reaches endian-typed member; "
                    "pointer/call is an interface lead only", source_type)
        return "insufficient", "no pointer-parameter or object-call lead", source_type
    return "insufficient", "RHS type or conversion cannot be established", source_type


def analyze_text(source: str, source_path: str = "<synthetic>",
                 declaration_files: dict[str, str] | None = None) -> dict:
    files = declaration_files or {source_path: source}
    report = analyze_text_v1(source, source_path, files)
    layouts = type_layouts(files)
    clean = mask_comments_and_literals(source)
    findings = report["findings"]
    occupied = {(item["line"], item["object"], item["field"]) for item in findings}
    for function in FUNCTION_OPEN.finditer(clean):
        name = function.group(1)
        if name in CONTROL:
            continue
        opening = function.end() - 1
        closing = closing_delimiter(clean, opening, "{", "}")
        if closing is None:
            continue
        body = clean[opening + 1:closing]
        params = function.group(2)
        param_pointers = {item.group("name") for item in OBJECT_DECL.finditer(params)
                          if item.group("pointer")}
        for pattern, kind in ((PATH_ASSIGNMENT, "path_assignment"),
                              (WIDE_ALIAS, "wide_alias_store")):
            for site in pattern.finditer(body):
                path = site.group("path")
                root, parts = path_parts(path)
                line = line_number(source, opening + 1 + site.start())
                if (line, root, parts[-1]) in occupied:
                    continue
                prefix = params + ";" + body[:site.start()]
                roots = {item.group("name"): " ".join(item.group("type").split())
                         for item in OBJECT_DECL.finditer(prefix)}
                resolved = resolved_member(path, roots, layouts)
                if resolved is None:
                    continue
                member, siblings, position = resolved
                rhs = source[opening + 1 + site.start("rhs"):
                             opening + 1 + site.end("rhs")]
                scalars = {item.group("name"): " ".join(item.group("type").split())
                           for item in HOST_DECL.finditer(prefix)}
                interface = []
                if root in param_pointers:
                    interface.append({"kind": "pointer_parameter", "name": root,
                                      "note": "possible caller-visible object, not consumer proof"})
                if kind == "path_assignment":
                    if not re.fullmatch(r"__(?:le|be)(?:16|32|64)", member["type"]):
                        continue
                    status, reason, source_type = extended_status(
                        rhs, member["type"], scalars, interface)
                    destination = member["type"]
                else:
                    next_member = siblings[position + 1] if position + 1 < len(siblings) else None
                    endian_siblings = {
                        match.group(1) for sibling in siblings
                        if (match := re.fullmatch(r"__(le|be)(?:16|32|64)",
                                                 sibling["type"]))
                    }
                    if not (member["type"] == "u8" and next_member
                            and next_member["type"] == "u8"
                            and next_member["count"] == 3
                            and len(endian_siblings) == 1):
                        continue
                    expected = next(iter(endian_siblings))
                    cast = site.group("cast")
                    converted = re.fullmatch(rf"cpu_to_{expected}32\s*\((.*)\)",
                                             rhs.strip(), re.S)
                    conversion_input = (rhs_type(converted.group(1), scalars)
                                        if converted else None)
                    if (cast == f"__{expected}32" and conversion_input in
                            {"u8", "u16", "u32", "s8", "s16", "s32",
                             "unsigned int"}):
                        status, reason = "normal", "explicit 32-bit conversion at aliased slot"
                    elif cast == "u32" and not converted and interface:
                        status, reason = (
                            "candidate", "native 32-bit alias store spans u8 plus u8[3] "
                            "beside endian-typed fields; verify slot's protocol byte order")
                    else:
                        status, reason = "insufficient", "wide alias slot representation uncertain"
                    source_type = cast
                    destination = f"u8+u8[3] (adjacent __{expected} fields)"
                findings.append({
                    "status": status, "reason": reason,
                    "function": name, "assignment_kind": kind,
                    "source_file": source_path, "line": line,
                    "object": root, "struct": roots[root], "field": parts[-1],
                    "path": " ".join(path.split()), "destination_type": destination,
                    "rhs": " ".join(rhs.split()), "source_type": source_type,
                    "declaration": [{"file": member["file"], "line": member["line"],
                                     "type": member["type"]}],
                    "interface_evidence": interface,
                })
                occupied.add((line, root, parts[-1]))
    counts = Counter(item["status"] for item in findings)
    report["findings"] = sorted(findings,
                                key=lambda item: (item["line"], item["field"]))
    report["counts"] = {status: counts[status]
                        for status in ("candidate", "normal", "insufficient")}
    report["scope"] = (
        "One C revision plus quoted includes up to three edges. Direct, nested "
        "and array member stores require a resolved declaration; wide alias "
        "review leads require an adjacent u8 plus u8[3] slot and same-order "
        "annotated siblings. Pointer parameters are interface hints, not "
        "proof of hardware consumption. Normal is local to a write site.")
    return report


def analyze_revision(linux_dir: Path, revision: str, source_path: str) -> dict:
    files, skipped = source_tree(linux_dir, revision, source_path)
    if source_path not in files:
        raise FileNotFoundError(f"source absent at revision {revision}: {source_path}")
    # The original reader stops after two quoted include edges. One extra,
    # bounded edge reaches descriptor layouts included by local helper headers.
    for path, contents in list(files.items()):
        for include in QUOTED_INCLUDE.finditer(contents):
            child = local_include_path(path, include.group(1))
            if child is None or child in files or len(files) >= 64:
                continue
            child_source = git_file(linux_dir, revision, child)
            if child_source is None:
                skipped.append(f"unavailable third-edge include: {child}")
            else:
                files[child] = child_source
    report = analyze_text(files[source_path], source_path, files)
    report["revision"] = revision
    report["files_read"] = [{"path": path, "sha256": sha256(contents)}
                            for path, contents in files.items()]
    report["include_notes"] = skipped
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze_revision(args.linux_dir, args.revision, args.source)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
