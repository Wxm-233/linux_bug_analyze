"""Bounded structure-field to HCI byte-copy evidence in one Git revision.

This follows declarations and a known byte forwarding chain. It is a review
lead extractor: a host-to-endian field assignment is a conditional candidate,
not a protocol, configuration, hardware or defect verdict. No patch is read.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
from collections import Counter
from pathlib import Path

import outbound_scalar_single_revision as scalar
from endian_consumer_single_revision import closing_delimiter, digest, git_file, mask_comments_and_literals

VERSION = "structured-hci-single-revision-v1.0"
IDENT = scalar.IDENT
FIXED = r"(?:u(?:16|32|64)|__u(?:16|32|64)|__(?:le|be)(?:16|32|64))"
HCI = "include/net/bluetooth/hci.h"
HCI_CORE = "include/net/bluetooth/hci_core.h"
STATUS = ("candidate", "matched_conversion", "insufficient")


def reachable_files(source_path: str, files: dict[str, str]) -> set[str]:
    """Only direct include spellings within the bounded files, at <= 8 edges."""
    pending, seen = [(source_path, 0)], set()
    while pending:
        path, depth = pending.pop()
        if path in seen or path not in files:
            continue
        seen.add(path)
        if depth >= 8:
            continue
        # Include directives are read from comment-masked source without masking
        # the quoted include string itself; ignore directives in block comments.
        source = re.sub(r"/\*.*?\*/|//[^\n]*", lambda m: "".join("\n" if char == "\n" else " " for char in m.group(0)), files[path], flags=re.S)
        for match in re.finditer(r'^\s*#\s*include\s*([<"])([^>"\n]+)[>"]', source, re.M):
            if scalar.conditional_at(files[path], match.start()):
                continue
            name = match.group(2)
            target = "include/" + name if match.group(1) == "<" else posixpath.normpath(posixpath.join(posixpath.dirname(path), name))
            if target in files:
                pending.append((target, depth + 1))
    return seen


def structs(files: dict[str, str]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for path, source in files.items():
        clean = mask_comments_and_literals(source)
        for match in re.finditer(rf"\bstruct\s+({IDENT})\s*\{{", clean):
            opening = match.end() - 1
            closing = closing_delimiter(clean, opening, "{", "}")
            if closing is None:
                continue
            body = clean[opening + 1:closing]
            depth, fields = 0, {}
            depths = []
            for char in body:
                depths.append(depth)
                depth += (char == "{") - (char == "}")
            for field in re.finditer(rf"\b({FIXED})\s+({IDENT})\s*;", body):
                if depths[field.start()] != 0:
                    continue
                start, end = opening + 1 + field.start(), opening + 1 + field.end()
                fields.setdefault(field.group(2), []).append({"type": field.group(1),
                    "conditional": scalar.conditional_at(source, start),
                    "evidence": scalar.evidence(path, source, start, end)})
            result.setdefault(match.group(1), []).append({"fields": fields,
                "conditional": scalar.conditional_at(source, match.start()),
                "evidence": scalar.evidence(path, source, match.start(), closing + 1)})
    return result


def field_declaration(declarations: dict, struct_name: str, field: str, reachable: set[str]) -> tuple[dict | None, str | None]:
    items = declarations.get(struct_name, [])
    if len(items) != 1:
        return None, "structure definition absent or ambiguous in bounded same-revision files"
    item = items[0]
    members = item["fields"].get(field, [])
    if len(members) != 1:
        return None, "direct fixed-width scalar field declaration absent or ambiguous"
    member = members[0]
    if item["conditional"] or member["conditional"]:
        return None, "unknown/inactive conditional structure or field declaration"
    if member["evidence"]["file"] not in reachable:
        return None, "field header is not reachable via bounded include spellings"
    return member, None


def scope_at(clean: str, fn: scalar.Function, offset: int) -> tuple[int, ...]:
    stack = [fn.opening]
    for pos in range(fn.opening + 1, offset):
        if clean[pos] == "{":
            stack.append(pos)
        elif clean[pos] == "}" and len(stack) > 1:
            stack.pop()
    return tuple(stack)


def local_object(clean: str, fn: scalar.Function, variable: str, call_offset: int) -> tuple[dict | None, str | None]:
    body = clean[fn.opening + 1:fn.closing]
    declared_by_start = {item.start(): item for item in scalar.declaration_spellings(body, variable)}
    # The shared scalar helper predates __u spellings; include them in shadow
    # inventory rather than letting a scalar shadow reuse an outer struct type.
    for item in re.finditer(rf"\b{FIXED}\s+\**\s*{re.escape(variable)}\b", body):
        declared_by_start[item.start()] = item
    known_name_offsets = {item.start() + list(re.finditer(rf"\b{re.escape(variable)}\b", item.group(0)))[-1].start()
                          for item in declared_by_start.values()}
    for item in re.finditer(rf"\b({IDENT})\s+\**\s*({re.escape(variable)})\b\s*(?=[\[;=])", body):
        if item.group(1) not in {"return", "goto", "case"} and item.start(2) not in known_name_offsets:
            declared_by_start[item.start()] = item
    declared = list(declared_by_start.values())
    call_scope = scope_at(clean, fn, call_offset)
    visible = []
    for item in declared:
        offset = fn.opening + 1 + item.start()
        scope = scope_at(clean, fn, offset)
        if offset < call_offset and call_scope[:len(scope)] == scope:
            visible.append((len(scope), offset))
    if not visible:
        return None, "no visible local declaration at this call; parameters are unsupported"
    depth = max(item[0] for item in visible)
    nearest = [item[1] for item in visible if item[0] == depth]
    if len(nearest) != 1:
        return None, "multiple declarations in the same visible lexical scope"
    pattern = rf"\bstruct\s+({IDENT})\s+{re.escape(variable)}\s*;"
    found = [item for item in re.finditer(pattern, body) if fn.opening + 1 + item.start() == nearest[0]]
    if len(found) != 1:
        return None, "object is not one uninitialized direct local structure (pointer/array/initializer unsupported)"
    match = found[0]
    start, end = fn.opening + 1 + match.start(), fn.opening + 1 + match.end()
    return {"struct": match.group(1), "start": start, "end": end, "scope": scope_at(clean, fn, start)}, None


def source_pointer(clean: str, fn: scalar.Function, variable: str) -> tuple[str | None, str | None]:
    parts = scalar.split_arguments(fn.parameters) or []
    matches = []
    for part in parts:
        found = re.fullmatch(rf"(?:const\s+)?struct\s+({IDENT})\s*\*\s*{re.escape(variable)}", part.strip())
        if found:
            matches.append(found.group(1))
    body = clean[fn.opening + 1:fn.closing]
    local = list(re.finditer(rf"\b(?:const\s+)?struct\s+({IDENT})\s*\*\s*{re.escape(variable)}\s*=\s*({IDENT})\s*->\s*({IDENT})\s*;", body))
    spellings = scalar.declaration_spellings(body, variable)
    known_local_names = {re.search(rf"\b{re.escape(variable)}\b", item.group(0)).start() + item.start()
                         for item in local}
    # Typedef names are deliberately not resolved here. Detect unknown local
    # declarator spellings too, so they cannot silently inherit a parameter's
    # struct type. Array forms are included even when the typedef is unknown.
    for item in re.finditer(rf"\b({IDENT})\s+\**\s*({re.escape(variable)})\b\s*(?=[\[;=])", body):
        if item.group(1) in {"return", "goto", "case"}:
            continue
        if item.start(2) not in known_local_names:
            return None, "unsupported local same-name declarator/typedef prevents source-pointer binding"
    for item in scalar.standalone(body, variable):
        before, after = body[:item.start()].rstrip(), body[item.end():].lstrip()
        if item.start() in known_local_names:
            continue
        if (after.startswith("[") or re.match(r"\)\s*->", after)
                or before.endswith("*") or (before.endswith("&") and not after.startswith("->"))):
            return None, "complex/parenthesized/indexed source-pointer use or unknown escape is unsupported"
    if len(matches) == 1 and not spellings:
        struct_name, expected_writes = matches[0], 0
    elif not matches and len(local) == 1 and len(spellings) == 1:
        item = local[0]
        # A declaration's pointer type is the bounded type fact. The upstream
        # member value, nullability and interprocedural aliases stay unproven.
        upstream = item.group(2)
        if not any(re.fullmatch(rf"(?:const\s+)?struct\s+{IDENT}\s*\*\s*{re.escape(upstream)}", part.strip()) for part in parts):
            return None, "local source pointer is not initialized from a direct struct-pointer parameter member"
        first_access = re.search(rf"\b{re.escape(variable)}\s*->", body)
        if not first_access or item.end() >= first_access.start():
            return None, "local source pointer is not declared before its member use"
        declaration_scope = scope_at(clean, fn, fn.opening + 1 + item.start())
        use_scope = scope_at(clean, fn, fn.opening + 1 + first_access.start())
        if use_scope[:len(declaration_scope)] != declaration_scope:
            return None, "local source pointer declaration is outside the member-use lexical scope"
        struct_name, expected_writes = item.group(1), 1
    else:
        return None, "source pointer lacks a unique parameter or simple initialized local declaration; shadowing unsupported"
    if len(scalar.writes(body, variable)) != expected_writes or re.search(rf"&\s*{re.escape(variable)}\b(?!\s*->)", body):
        return None, "source pointer was reassigned or its address escaped"
    return struct_name, None


def host_member(clean: str, fn: scalar.Function, expression: str, bits: int,
                declarations: dict, reachable: set[str], macros: set[str]) -> tuple[dict | None, str | None]:
    expression = expression.strip()
    found = re.fullmatch(rf"({IDENT})\s*->\s*({IDENT})", expression)
    if not found:
        return None, "source is not a direct one-level struct-pointer member"
    variable, field = found.groups()
    struct_name, reason = source_pointer(clean, fn, variable)
    if reason:
        return None, reason
    declaration, reason = field_declaration(declarations, struct_name, field, reachable)
    if reason:
        return None, reason
    if declaration["type"] not in (f"u{bits}", f"__u{bits}"):
        return None, "source field is not a matching-width host unsigned field"
    if any(name in macros for name in (variable, field, struct_name, declaration["type"])):
        return None, "source variable/member/type is macro-defined in bounded files"
    # Type annotation alone does not prove prior representation or values. Refuse
    # explicit writes and member address escapes in this function. Opaque uses
    # of the pointer are retained as an explicit provenance limitation below.
    body = clean[fn.opening + 1:fn.closing]
    access = rf"\b{re.escape(variable)}\s*->\s*{re.escape(field)}\b"
    if re.search(access + r"\s*(?:=(?!=)|[+\-*/%&|^]=|<<=|>>=|\+\+|--)", body) or re.search(r"&\s*" + access, body):
        return None, "source member is written or its address escaped in this function"
    return {"struct": struct_name, "pointer": variable, "field": field,
            "declaration": declaration, "source_value_paths": "not_proven",
            "representation_provenance": "host declaration only; initialization and interprocedural values not proven"}, None


def analyze_files(source_path: str, files: dict[str, str], revision: str = "synthetic") -> dict:
    if source_path not in files:
        raise FileNotFoundError(source_path)
    if len(files) > 64 or any(len(source.encode("utf-8")) > scalar.MAX_SOURCE_BYTES for source in files.values()):
        raise ValueError("bounded source inventory exceeded")
    source = files[source_path]
    clean = mask_comments_and_literals(source)
    declarations, reachable, macros = structs(files), reachable_files(source_path, files), scalar.macro_names(files)
    consumer = scalar.prove_consumer_chain(files, "hci_req_add")
    findings, sites = [], []
    for fn in scalar.functions(clean):
        for call in scalar.calls(clean, fn, "hci_req_add"):
            args = call["args"]
            if len(args) != 4:
                continue
            found = re.fullmatch(rf"&\s*({IDENT})", args[3])
            if not found:
                continue
            variable = found.group(1)
            obj, reason = local_object(clean, fn, variable, call["start"])
            if obj is None:
                sites.append({"status": "insufficient", "reason": reason,
                              "call": scalar.evidence(source_path, source, call["start"], call["end"])})
                continue
            site = {"function": fn.name, "variable": variable, "struct": obj["struct"],
                    "call": scalar.evidence(source_path, source, call["start"], call["end"]),
                    "object_declaration": scalar.evidence(source_path, source, obj["start"], obj["end"]),
                    "arguments": args, "consumer": consumer}
            problem = None
            if obj["end"] >= call["start"] or tuple(obj["scope"]) != scope_at(clean, fn, call["start"]):
                problem = "declaration and call are not ordered in the same lexical block"
            elif not re.fullmatch(rf"sizeof\s*\(\s*{re.escape(variable)}\s*\)", args[2]):
                problem = "length is not sizeof the exact structure object"
            elif (scalar.conditional_at(source, fn.start) or scalar.conditional_at(source, call["start"])
                  or re.search(r"^\s*#", clean[fn.opening + 1:fn.closing], re.M)):
                problem = "unknown/inactive conditional or preprocessor directive in producer function"
            elif any(name in macros for name in (variable, obj["struct"], "hci_req_add")):
                problem = "object/type/entry is macro-defined in bounded files"
            elif consumer["status"] != "proven_byte_copy_chain":
                problem = "same-revision byte copy chain not proven: " + consumer["reason"]
            region = clean[obj["end"]:call["start"]]
            if re.search(r"\bgoto\b", region):
                problem = problem or "goto prevents bounded straight-block ordering proof"
            if re.search(rf"&\s*{re.escape(variable)}\b", region):
                problem = problem or "object/member address escaped before send"
            assignments = []
            assignment_pattern = re.compile(rf"\b{re.escape(variable)}\s*\.\s*({IDENT})\s*=(?!=)\s*([^;]*);")
            residual = list(region)
            for match in assignment_pattern.finditer(region):
                start, end = obj["end"] + match.start(), obj["end"] + match.end()
                before = region[:match.start()].rstrip()
                statement_ok = not before or before[-1] in ";{}"
                assignments.append({"field": match.group(1), "expression": match.group(2).strip(),
                                    "start": start, "end": end, "statement_ok": statement_ok,
                                    "same_scope": scope_at(clean, fn, start) == tuple(obj["scope"])})
                for index in range(match.start(), match.end()):
                    residual[index] = " "
            if scalar.standalone("".join(residual), variable):
                problem = problem or "unsupported object/member reference, whole-object write, alias or compound update before send"
            site.update(status="insufficient" if problem else "bounded_structure_send", reason=problem)
            sites.append(site)
            for assignment in assignments:
                declaration, field_problem = field_declaration(declarations, obj["struct"], assignment["field"], reachable)
                # Missing declaration is a retained unknown, not an assumed
                # endian contract. Host-only fields are outside this rule.
                if declaration and not declaration["type"].startswith(("__le", "__be")):
                    continue
                finding = {"function": fn.name, "variable": variable, "struct": obj["struct"],
                           "field": assignment["field"], "assignment": scalar.evidence(source_path, source, assignment["start"], assignment["end"]),
                           "call": site["call"], "object_declaration": site["object_declaration"],
                           "target_declaration": declaration, "consumer": consumer,
                           "source_value_paths": "not_proven", "defect_verdict": "not assessed",
                           "required_payload_format": "same-revision field declaration only; external consumer/opcode format and hardware reachability unproven"}
                field_problem = problem or field_problem
                if not assignment["statement_ok"] or not assignment["same_scope"]:
                    field_problem = field_problem or "assignment is conditional/nested or not a direct statement in the object block"
                if sum(item["field"] == assignment["field"] for item in assignments) != 1:
                    field_problem = field_problem or "field has multiple assignments before this send"
                source_proof = None
                status = "insufficient"
                if not field_problem:
                    target = declaration["type"]
                    endian, bits = target[2:4], int(target[4:])
                    if any(name in macros for name in (assignment["field"], target)):
                        field_problem = "target field/type is macro-defined in bounded files"
                    expression = assignment["expression"]
                    convert = re.fullmatch(rf"cpu_to_{endian}{bits}\s*\(\s*({IDENT}\s*->\s*{IDENT})\s*\)", expression)
                    if convert and not field_problem:
                        if f"cpu_to_{endian}{bits}" in macros:
                            field_problem = "conversion is redefined in bounded files"
                        else:
                            source_proof, field_problem = host_member(clean, fn, convert.group(1), bits, declarations, reachable, macros)
                        if not field_problem:
                            status = "matched_conversion"
                    elif not field_problem:
                        source_proof, source_problem = host_member(clean, fn, expression, bits, declarations, reachable, macros)
                        field_problem = field_problem or source_problem
                        if not field_problem:
                            status = "candidate"
                finding.update(status=status, source_member=source_proof, reason=field_problem or (
                    "host-declared member assigned without conversion to an endian-declared payload field; exact byte copy reaches memcpy, representation may disagree on opposite-endian hosts" if status == "candidate" else
                    "one matching explicit Linux host-to-endian conversion before byte copy; only this field representation syntax is satisfied"))
                finding["declaration_binding"] = {"status": "bounded_lexical_declaration" if declaration and source_proof else "insufficient",
                    "target": declaration, "source": source_proof,
                    "qualification": "same-revision direct scalar fields and spelling-based lexical binding; no compiler AST/complete preprocessing"}
                finding["producer_representation"] = {"status": status,
                    "source_annotation": source_proof["declaration"]["type"] if source_proof else "unproven",
                    "target_annotation": declaration["type"] if declaration else "unproven",
                    "expression": assignment["expression"], "source_value_paths": "not_proven",
                    "source_host_numeric_value": "not_proven; host annotation alone does not exclude previously encoded runtime values"}
                finding["copy_chain"] = consumer
                finding["reader_or_schema"] = {"status": "declaration_only" if declaration else "unproven",
                    "same_revision_payload_field": declaration,
                    "external_controller_contract": "unproven", "opcode_to_payload_schema_binding": "unproven"}
                finding["applicability"] = {"status": "conditional_source_lead",
                    "runtime_path": "unproven", "compiled_configuration": "unproven",
                    "architecture_difference": "requires a host byte order differing from declared payload encoding and a reachable byte-copy path"}
                finding["suggested_check"] = {
                    "kind": "conditional_representation_check" if status == "candidate" else "none",
                    "preconditions": ["same-revision target field actually uses the declared endian format",
                        "source member actually contains a host numeric value", "this producer and byte-copy path run in the applicable configuration",
                        "confirm opcode-specific controller contract before proposing any edit"],
                    "action": "verify host-to-payload encoding at the field boundary; do not automatically insert a conversion",
                    "automated_patch": False}
                findings.append(finding)
    counts = Counter(item["status"] for item in findings)
    return {"version": VERSION, "revision": revision, "source_file": source_path,
            "files_read": [{"path": path, "sha256": digest(contents), "include_reachable_from_producer": path in reachable} for path, contents in files.items()],
            "consumer_proof": consumer, "sites": sites, "findings": findings,
            "counts": {status: counts[status] for status in STATUS},
            "scope": "Direct local struct object and one-layer endian field assignments from matching-width host struct-pointer parameter or simple declared local-pointer members; same-block sizeof(object)/&object at hci_req_add. Zero findings is out of scope, never normal. Source type spelling and bounded copy evidence do not establish a hardware defect.",
            "assumptions": ["Linux fixed-width, __le/__be and cpu_to_le/be type/conversion spellings retain normal semantics unless redefined in bounded files", "__KERNEL__=true; simple include guards and kernel ifdef only, other configurations remain unknown", "bounded include reachability is spelling-based and is not a preprocessed translation unit", "function/block extraction is lexical; no full C AST or control-flow, no layout/padding, no opcode schema, no compiled applicability or hardware execution", "source host field annotations supply conditional representation evidence; source initialization/interprocedural value provenance not proven", "typedef resolution and complex declarator syntax are unsupported; identified same-name declarators and complex source-pointer uses are conservatively refused"],
            "dependencies": [{"path": Path(scalar.__file__).name, "sha256": digest(Path(scalar.__file__).read_text(encoding="utf-8"))},
                             {"path": "endian_consumer_single_revision.py", "sha256": digest(Path(__file__).with_name("endian_consumer_single_revision.py").read_text(encoding="utf-8"))}]}


def analyze_revision(linux_dir: Path, revision: str, source_path: str) -> dict:
    files, blobs = {}, {}
    for path in dict.fromkeys((source_path, scalar.REQUEST, scalar.SKBUFF, HCI, HCI_CORE)):
        source = git_file(linux_dir, revision, path)
        if source is not None:
            files[path] = source
            process = subprocess.run(["git", "rev-parse", f"{revision}:{path}"], cwd=linux_dir, capture_output=True, check=True, text=True)
            blobs[path] = process.stdout.strip()
    report = analyze_files(source_path, files, revision)
    for item in report["files_read"]:
        item["git_blob"] = blobs[item["path"]]
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
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
