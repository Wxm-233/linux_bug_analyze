"""Bounded same-revision scalar-to-byte evidence for HCI command entries.

This is a review-lead extractor, never an opcode payload-format oracle. A
raw_host_bytes finding means bytes of a declared host scalar reach memcpy;
it does not establish what encoding the device expects. matched_endian_scalar
means a unique local scalar has a matching explicit Linux conversion, not that
the particular command accepts that representation. Unsupported flow refuses.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from endian_consumer_single_revision import (
    closing_delimiter, digest, git_file, line_number, mask_comments_and_literals,
)

VERSION = "outbound-scalar-single-revision-v1.0"
IDENT = r"[A-Za-z_]\w*"
TYPE = r"(?:u(?:16|32|64)|__(?:le|be)(?:16|32|64))"
REQUEST = "net/bluetooth/hci_request.c"
SKBUFF = "include/linux/skbuff.h"
MAX_SOURCE_BYTES = 2_000_000
MAX_FUNCTIONS = 2000
MAX_CALLS = 1000
CONTROL = {"if", "while", "for", "switch", "sizeof"}


@dataclass(frozen=True)
class Function:
    name: str
    parameters: str
    start: int
    opening: int
    closing: int


def functions(clean: str) -> list[Function]:
    """Only file-scope, non-nested-parameter C function definitions."""
    result = []
    depth_at = []
    depth = 0
    for char in clean:
        depth_at.append(depth)
        depth += (char == "{") - (char == "}")
    pattern = re.compile(rf"\b({IDENT})\s*\(([^;{{}}()]*)\)\s*\{{", re.S)
    for match in pattern.finditer(clean):
        if depth_at[match.start()] or match.group(1) in CONTROL:
            continue
        opening = match.end() - 1
        closing = closing_delimiter(clean, opening, "{", "}")
        if closing is not None:
            result.append(Function(match.group(1), match.group(2), match.start(), opening, closing))
    if len(result) > MAX_FUNCTIONS:
        raise ValueError("function extraction bound exceeded")
    return result


def split_arguments(text: str) -> list[str] | None:
    depth = 0
    arguments, start = [], 0
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth < 0:
                return None
        elif char == "," and not depth:
            arguments.append(text[start:index].strip())
            start = index + 1
    if depth:
        return None
    arguments.append(text[start:].strip())
    return arguments


def calls(clean: str, function: Function, name: str | None = None) -> list[dict]:
    body = clean[function.opening + 1:function.closing]
    pattern = re.compile(rf"\b({re.escape(name) if name else IDENT})\s*\(")
    result = []
    for match in pattern.finditer(body):
        offset = function.opening + 1 + match.start()
        preceding = clean[:offset].rstrip()
        if preceding.endswith((".", "->")):
            continue
        opening = function.opening + 1 + match.end() - 1
        closing = closing_delimiter(clean, opening, "(", ")")
        if closing is None or closing > function.closing:
            continue
        args = split_arguments(clean[opening + 1:closing])
        if args is not None:
            result.append({"name": match.group(1), "start": offset,
                           "end": closing + 1, "args": args})
    if len(result) > MAX_CALLS:
        raise ValueError("call extraction bound exceeded")
    return result


def standalone(text: str, name: str) -> list[re.Match]:
    """Exclude member spellings such as pointer->plen and hdr.plen."""
    matches = []
    for match in re.finditer(rf"\b{re.escape(name)}\b", text):
        preceding = text[:match.start()].rstrip()
        if not preceding.endswith((".", "->")):
            matches.append(match)
    return matches


def writes(text: str, name: str) -> list[int]:
    result = []
    for match in standalone(text, name):
        before, after = text[:match.start()].rstrip(), text[match.end():].lstrip()
        if (re.match(r"(?:=(?!=)|[+\-*/%&|^]=|<<=|>>=|\+\+|--)", after)
                or before.endswith(("++", "--"))):
            result.append(match.start())
    return result


def macro_names(files: dict[str, str]) -> set[str]:
    return {match.group(1) for source in files.values()
            for match in re.finditer(rf"^\s*#\s*(?:define|undef)\s+({IDENT})\b",
                                      mask_comments_and_literals(source), re.M)}


def conditional_at(source: str, offset: int) -> bool:
    """Reject unknown/inactive branches; assume only __KERNEL__ is true."""
    clean = mask_comments_and_literals(source)
    directives = list(re.finditer(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif|define)\b([^\n]*)", clean, re.M))
    guard = None
    if len(directives) >= 2:
        first, second = directives[:2]
        if (first.group(1) == "ifndef"
                and re.fullmatch(IDENT, first.group(2).strip())
                and second.group(1) == "define"
                and second.group(2).strip() == first.group(2).strip()
                and not clean[:first.start()].strip()):
            guard = first.start()
    stack = []
    kernel_redefined = bool(re.search(r"^\s*#\s*(?:define|undef)\s+__KERNEL__\b", clean[:offset], re.M))
    for directive in directives:
        if directive.start() >= offset:
            break
        kind = directive.group(1)
        if kind in {"if", "ifdef", "ifndef"}:
            symbol = directive.group(2).strip()
            if directive.start() == guard:
                stack.append(True)
            elif symbol == "__KERNEL__" and kind in {"ifdef", "ifndef"} and not kernel_redefined:
                stack.append(kind == "ifdef")
            else:
                stack.append(None)
        elif kind == "endif" and stack:
            stack.pop()
        elif kind == "else" and stack:
            stack[-1] = None if stack[-1] is None else not stack[-1]
        elif kind == "elif" and stack:
            stack[-1] = None
    return any(item is not True for item in stack)


def evidence(path: str, source: str, start: int, end: int) -> dict:
    return {"file": path, "line": line_number(source, start),
            "text": " ".join(source[start:end].split()), "source_sha256": digest(source)}


def parameter_names(parameters: str) -> list[str] | None:
    args = split_arguments(parameters)
    if args is None:
        return None
    names = []
    for arg in args:
        found = re.search(rf"\b({IDENT})\s*$", arg)
        if not found or "(" in arg or "[" in arg:
            return None
        names.append(found.group(1))
    return names


def prove_consumer_chain(files: dict[str, str], entry: str = "__hci_cmd_sync") -> dict:
    """Prove only this exact scalar-length/byte-pointer forwarding route."""
    prefixes = {
        "__hci_cmd_sync": [
            (REQUEST, "__hci_cmd_sync", 2, 3, "__hci_cmd_sync_ev", 2, 3),
            (REQUEST, "__hci_cmd_sync_ev", 2, 3, "hci_req_add_ev", 2, 3),
        ],
        "hci_req_add": [(REQUEST, "hci_req_add", 2, 3, "hci_req_add_ev", 2, 3)],
    }
    if entry not in prefixes:
        return {"status": "insufficient", "reason": "unsupported consumer entry", "chain": []}
    specs = prefixes[entry] + [
        (REQUEST, "hci_req_add_ev", 2, 3, "hci_prepare_cmd", 2, 3),
        (REQUEST, "hci_prepare_cmd", 2, 3, "skb_put_data", 2, 1),
        (SKBUFF, "skb_put_data", 2, 1, "memcpy", 2, 1),
    ]
    chain = []
    macros = macro_names(files)
    for path, function_name, length_index, data_index, next_name, next_length, next_data in specs:
        if path not in files:
            return {"status": "insufficient", "reason": f"missing same-revision consumer file: {path}", "chain": chain}
        source = files[path]
        clean = mask_comments_and_literals(source)
        definitions = [fn for fn in functions(clean) if fn.name == function_name]
        if len(definitions) != 1 or function_name in macros or next_name in macros:
            return {"status": "insufficient", "reason": f"ambiguous definition or macro: {function_name}/{next_name}", "chain": chain}
        fn = definitions[0]
        params = parameter_names(fn.parameters)
        if not params or max(length_index, data_index) >= len(params):
            return {"status": "insufficient", "reason": f"unsupported signature: {function_name}", "chain": chain}
        length, data = params[length_index], params[data_index]
        parameter_parts = split_arguments(fn.parameters)
        if (not re.fullmatch(rf"(?:u32|unsigned\s+int)\s+{length}", parameter_parts[length_index])
                or not re.fullmatch(rf"const\s+void\s*\*\s*{data}", parameter_parts[data_index])):
            return {"status": "insufficient", "reason": f"consumer pointer/length signature not proven: {function_name}", "chain": chain}
        body = clean[fn.opening + 1:fn.closing]
        forwards = calls(clean, fn, next_name)
        if len(forwards) != 1:
            return {"status": "insufficient", "reason": f"not one direct forwarding call: {function_name}", "chain": chain}
        call = forwards[0]
        args = call["args"]
        if (max(next_length, next_data) >= len(args)
                or args[next_length] != length or args[next_data] != data):
            return {"status": "insufficient", "reason": f"transformed/aliased pointer or length: {function_name}", "chain": chain}
        if (conditional_at(source, fn.start) or re.search(r"^\s*#", body, re.M)
                or writes(body, length) or writes(body, data)
                or re.search(rf"&\s*(?:{length}|{data})\b", body)
                or re.search(rf"\*\s*{data}\s*=", body)):
            return {"status": "insufficient", "reason": f"conditional or modified forwarding parameter: {function_name}", "chain": chain}
        if len(standalone(body, data)) != 1:
            return {"status": "insufficient", "reason": f"pointer referenced outside its unique forwarding argument: {function_name}", "chain": chain}
        for parameter in (length, data):
            if declaration_spellings(body, parameter) or parameter in macros:
                return {"status": "insufficient", "reason": f"shadowed/macro forwarding parameter: {function_name}", "chain": chain}
        for other in calls(clean, fn):
            if other["start"] != call["start"] and other["name"] not in CONTROL:
                if any(standalone(arg, data) for arg in other["args"]):
                    return {"status": "insufficient", "reason": f"pointer also passed to opaque call: {function_name}", "chain": chain}
        chain.append({"function": function_name, "pointer_parameter": data,
                      "length_parameter": length,
                      "definition": evidence(path, source, fn.start, fn.opening),
                      "forward_call": evidence(path, source, call["start"], call["end"]),
                      "forward_arguments": args})
    return {"status": "proven_byte_copy_chain", "chain": chain,
            "terminal_semantics": "standard Linux memcpy copies source bytes without per-payload conversion",
            "payload_format": "not established; opcode-specific format evidence is required"}


def declarations(clean: str, fn: Function, variable: str) -> list[dict]:
    result = []
    parts = split_arguments(fn.parameters) or []
    for part in parts:
        found = re.fullmatch(rf"(?:const\s+)?({TYPE})\s+{re.escape(variable)}", part)
        if found:
            result.append({"type": found.group(1), "parameter": True,
                           "start": fn.start, "end": fn.opening, "initial": None})
    body = clean[fn.opening + 1:fn.closing]
    pattern = re.compile(rf"\b({TYPE})\s+{re.escape(variable)}\s*(?:=\s*([^;]*))?;")
    for match in pattern.finditer(body):
        result.append({"type": match.group(1), "parameter": False,
                       "start": fn.opening + 1 + match.start(),
                       "end": fn.opening + 1 + match.end(), "initial": match.group(2)})
    return result


def declaration_spellings(body: str, variable: str) -> list[re.Match]:
    return list(re.finditer(rf"\b(?:{TYPE}|int|char|long|short|void|bool|size_t|unsigned(?:\s+(?:int|long|short))?|signed(?:\s+(?:int|long|short))?|struct\s+{IDENT})\s+\**\s*{re.escape(variable)}\b", body))


def nonnegative_literal(expression: str, bits: int) -> bool:
    found = re.fullmatch(r"(0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)([uUlL]*)", expression.strip())
    if not found or found.group(2).lower() not in {"", "u", "l", "ul", "lu", "ll", "ull", "llu"}:
        return False
    number = found.group(1)
    base = 16 if number.lower().startswith("0x") else 8 if number.startswith("0") else 10
    return int(number, base) < (1 << bits)


def host_source_proof(clean: str, fn: Function, expression: str,
                      before_offset: int, bits: int, macros: set[str], depth: int = 0) -> tuple[bool, str]:
    """Prove source type and absence of explicit encoding, not all value paths.

    Branch assignments to the *input* host variable are not interpreted as a
    representation proof. No runtime/value-path claim follows from this check.
    The outbound endian destination still permits only one initializer.
    """
    expression = expression.strip()
    if nonnegative_literal(expression, bits):
        return True, "nonnegative literal fits the declared output width"
    if depth >= 4 or not re.fullmatch(IDENT, expression) or expression in macros:
        return False, "source is not a bounded host scalar or fitting nonnegative literal"
    declarations_found = declarations(clean, fn, expression)
    if len(declarations_found) != 1:
        return False, "source lacks a unique supported scalar declaration"
    item = declarations_found[0]
    if item["type"] != f"u{bits}" or item["start"] >= before_offset:
        return False, "source type is endian, unknown, mismatched-width, or declared too late"
    body = clean[fn.opening + 1:fn.closing]
    expected = 0 if item["parameter"] else 1
    if len(declaration_spellings(body, expression)) != expected:
        return False, "source has shadowing or ambiguous declarations"
    before = clean[fn.opening + 1:before_offset]
    if re.search(rf"&\s*{re.escape(expression)}\b", before):
        return False, "source address escaped before the conversion"
    assignment_region = clean[item["start"] if not item["parameter"] else fn.opening + 1:before_offset]
    # The input declaration may be filled along mutually exclusive branches.
    # Refuse explicit representation encoding and calls that could hide it.
    rhs_list = []
    if item["initial"] is not None:
        rhs_list.append(item["initial"])
    for occurrence in standalone(assignment_region, expression):
        tail = assignment_region[occurrence.end():]
        assigned = re.match(r"\s*=(?!=)\s*([^;]*);", tail)
        if assigned:
            rhs_list.append(assigned.group(1))
        elif (re.match(r"\s*(?:[+\-*/%&|^]=|<<=|>>=|\+\+|--)", tail)
              or assignment_region[:occurrence.start()].rstrip().endswith(("++", "--"))):
            return False, "source compound update has no representation proof"
    for rhs in rhs_list:
        if (re.search(r"\b(?:cpu_to_|le(?:16|32|64)_to_|be(?:16|32|64)_to_|__(?:le|be))(?:\w*)\b", rhs)
                or re.search(rf"\b{IDENT}\s*\(", rhs)):
            return False, "source is explicitly encoded or filled by an unknown call"
    if item["initial"] is not None:
        initial = item["initial"].strip()
        if not nonnegative_literal(initial, bits):
            if re.fullmatch(IDENT, initial) and initial != expression:
                proven, reason = host_source_proof(clean, fn, initial, item["start"], bits, macros, depth + 1)
                if not proven:
                    return False, reason
            else:
                return False, "source initializer is not a fitting literal or supported host scalar"
    return True, f"unique u{bits} host declaration with no explicit encoding/call provenance; source value paths not proven"


def scalar_flow(clean: str, fn: Function, call: dict, variable: str,
                declaration: dict, macros: set[str]) -> tuple[str, str]:
    type_name = declaration["type"]
    start = fn.opening + 1 if declaration["parameter"] else declaration["end"]
    before = clean[start:call["start"]]
    entire = clean[fn.opening + 1:fn.closing]
    # Catch declarations of the same identifier under a different scalar type,
    # including a nested scope. This purposely refuses valid harmless shadows.
    shadows = declaration_spellings(entire, variable)
    expected = 0 if declaration["parameter"] else 1
    if len(shadows) != expected:
        return "insufficient", "shadowing or another declaration prevents a unique local scalar"
    if variable in macros or type_name in macros or call["name"] in macros:
        return "insufficient", "macro-defined variable, type, or entry function"
    if writes(before, variable):
        return "insufficient", "representation flow not proven: assignment after declaration or multiple assignments"
    if re.search(rf"&\s*{re.escape(variable)}\b", clean[fn.opening + 1:call["start"]]):
        return "insufficient", "address already escaped or aliased before the output call"
    if not declaration["parameter"] and declaration["initial"] is None:
        return "insufficient", "local scalar has no initializer; value and representation are not proven"
    if type_name.startswith("u"):
        if not declaration["parameter"]:
            proven, reason = host_source_proof(clean, fn, declaration["initial"], declaration["start"], int(type_name[1:]), macros)
            if not proven:
                return "insufficient", "host storage initializer representation unproven: " + reason
        return "raw_host_bytes", "bytes of a fixed-width host-declared scalar reach memcpy; required opcode encoding is unproven"
    endian, bits = type_name[2:4], type_name[4:]
    initial = declaration["initial"]
    if declaration["parameter"]:
        return "insufficient", "endian-typed parameter representation has no local conversion proof"
    matched = re.fullmatch(rf"cpu_to_{endian}{bits}\s*\(\s*({IDENT}|(?:0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]*)\s*\)", initial.strip())
    if not matched:
        return "insufficient", "endian declaration lacks one matching explicit conversion initializer"
    conversion = f"cpu_to_{endian}{bits}"
    if conversion in macros:
        return "insufficient", "conversion is locally macro-defined; semantic meaning not proven"
    proven, reason = host_source_proof(clean, fn, matched.group(1), declaration["start"], int(bits), macros)
    if not proven:
        return "insufficient", "conversion source representation unproven: " + reason
    return "matched_endian_scalar", "unique local scalar initialized by matching Linux endian conversion of a supported host source and not overwritten before copy; opcode format and source value paths remain unproven"


def analyze_files(source_path: str, files: dict[str, str], revision: str = "synthetic") -> dict:
    if source_path not in files:
        raise FileNotFoundError(source_path)
    if any(len(source.encode("utf-8")) > MAX_SOURCE_BYTES for source in files.values()):
        raise ValueError("source byte bound exceeded")
    source = files[source_path]
    clean = mask_comments_and_literals(source)
    consumers = {entry: prove_consumer_chain(files, entry)
                 for entry in ("__hci_cmd_sync", "hci_req_add")}
    macros = macro_names(files)
    findings = []
    for fn in functions(clean):
        for call in calls(clean, fn):
            if call["name"] not in consumers:
                continue
            consumer = consumers[call["name"]]
            args = call["args"]
            if len(args) != (5 if call["name"] == "__hci_cmd_sync" else 4):
                continue
            pointer = re.fullmatch(rf"&\s*({IDENT})", args[3])
            if not pointer:
                # Direct address expressions exist but are outside scalar v1.
                if args[3].lstrip().startswith("&"):
                    findings.append({"status": "insufficient", "reason": "address is not a direct scalar identifier",
                                     "function": fn.name, "call": evidence(source_path, source, call["start"], call["end"]),
                                     "arguments": args, "consumer": consumer})
                continue
            variable = pointer.group(1)
            declaration_list = declarations(clean, fn, variable)
            record = {"variable": variable, "function": fn.name,
                      "call": evidence(source_path, source, call["start"], call["end"]),
                      "arguments": args, "consumer": consumer,
                      "declarations": [dict(item, evidence=evidence(source_path, source, item["start"], item["end"])) for item in declaration_list],
                      "required_payload_format": "unproven",
                      "source_value_paths": "not_proven",
                      "defect_verdict": "not assessed"}
            if len(declaration_list) == 1:
                flow_status, flow_reason = scalar_flow(clean, fn, call, variable, declaration_list[0], macros)
                record["local_scalar_flow"] = {"status": flow_status, "reason": flow_reason,
                    "scope": "local representation syntax/host declaration; neither compiled applicability nor consumer/opcode correctness"}
            reason = None
            if len(declaration_list) != 1:
                reason = "not exactly one supported fixed-width local or parameter declaration"
            elif not re.fullmatch(rf"sizeof\s*\(\s*{re.escape(variable)}\s*\)", args[2]):
                reason = "length is not sizeof the same direct scalar"
            elif declaration_list[0]["start"] >= call["start"]:
                reason = "declaration does not precede call"
            elif (conditional_at(source, fn.start)
                  or conditional_at(source, call["start"])
                  or re.search(r"^\s*#", clean[fn.opening + 1:fn.closing], re.M)):
                reason = "conditional compilation or macro directive in the function"
            elif consumer["status"] != "proven_byte_copy_chain":
                reason = "same-revision consumer chain not proven: " + consumer["reason"]
            if reason:
                status = "insufficient"
            else:
                status, reason = scalar_flow(clean, fn, call, variable, declaration_list[0], macros)
            record.update(status=status, reason=reason)
            findings.append(record)
    count = Counter(item["status"] for item in findings)
    return {"version": VERSION, "revision": revision, "source_file": source_path,
            "files_read": [{"path": path, "sha256": digest(contents)} for path, contents in files.items()],
            "consumer_proof": consumers, "findings": findings,
            "counts": {key: count[key] for key in ("raw_host_bytes", "matched_endian_scalar", "insufficient")},
            "scope": "Only direct &fixed-width scalar with sizeof(same scalar) at __hci_cmd_sync/hci_req_add, using the exact same-revision HCI-to-memcpy route. No opcode-format oracle, defect or reachability claim. Zero sites is out of scope, never normal.",
            "assumptions": ["__KERNEL__=true in this Linux kernel source context; only simple #ifdef/#ifndef on that symbol is interpreted, other configuration expressions remain unknown", "Linux fixed-width and __le/__be type spelling has its standard meaning", "Linux cpu_to_le/be conversion spelling and memcpy retain their documented semantics unless redefined in the bounded files read", "included-header macro expansion and complete C compilation are not modeled"]}


def analyze_revision(linux_dir: Path, revision: str, source_path: str) -> dict:
    files = {}
    for path in dict.fromkeys((source_path, REQUEST, SKBUFF)):
        source = git_file(linux_dir, revision, path)
        if source is not None:
            files[path] = source
    return analyze_files(source_path, files, revision)


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
