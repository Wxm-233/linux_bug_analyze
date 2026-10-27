"""Find narrow endian-typed field *write* review leads in one Git revision.

This intentionally reads one C file at one revision. A lead requires a direct
host-typed scalar assignment to a same-width __le*/__be* struct field and a
later call passing that object by address. The call is boundary evidence, not
proof of a device contract. Results are sites to inspect, not defect verdicts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from endian_consumer_single_revision import (
    FUNCTION_OPEN, STRUCT_OPEN, closing_delimiter, line_number,
    mask_comments_and_literals, source_tree,
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


def analyze_text(source: str, source_path: str = "<synthetic>",
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


def analyze_revision(linux_dir: Path, revision: str, source_path: str) -> dict:
    files, skipped = source_tree(linux_dir, revision, source_path)
    if source_path not in files:
        raise FileNotFoundError(f"source absent at revision {revision}: {source_path}")
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
