"""One-revision check of simple typed-macro field accesses across byte orders.

This narrow prototype reads only files at one Git commit. It recognizes a
macro whose body accesses a named ``struct T`` through a field parameter,
collects literal field paths passed to that macro, and compiles those accesses
with the same revision's declarations on two real compiler ABIs. A diagnostic
for a missing top-level member is a review candidate, not a defect verdict.
Unsupported consumer forms and unproved build reachability remain explicit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from bcachefs_auto_layout_extract import (
    blank_comments,
    declarations,
    dependency_order,
    git_output,
)


IDENT = r"[A-Za-z_]\w*"
TYPED_ACCESS = re.compile(
    rf"\(\(\s*struct\s+(?P<type>{IDENT})\s*\*\s*\)\s*"
    rf"(?:NULL|0)\s*\)\s*->\s*(?P<field_param>{IDENT})\b"
)
LITERAL_PATH = re.compile(rf"{IDENT}(?:\.{IDENT})*")
MISSING_MEMBER = re.compile(r"has no member named ['‘`](?P<member>[A-Za-z_]\w*)['’`]")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def line_at(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


@dataclass(frozen=True)
class Macro:
    name: str
    params: tuple[str, ...]
    body: str
    first_line: int
    last_line: int


def macros(source: str) -> list[Macro]:
    """Join conventional backslash-continued function-like #defines."""
    lines = source.splitlines()
    found: list[Macro] = []
    index = 0
    while index < len(lines):
        first = index
        pieces = [lines[index]]
        while pieces[-1].rstrip().endswith("\\") and index + 1 < len(lines):
            index += 1
            pieces.append(lines[index])
        joined = "\n".join(pieces)
        match = re.match(
            rf"\s*#\s*define\s+(?P<name>{IDENT})\((?P<params>[^)]*)\)"
            rf"(?P<body>[\s\S]*)", joined
        )
        if match:
            params = tuple(part.strip() for part in match["params"].split(","))
            found.append(Macro(match["name"], params, match["body"],
                               first + 1, index + 1))
        else:
            # Object-like macros can enclose a typed macro's invocation.
            object_macro = re.match(
                rf"\s*#\s*define\s+(?P<name>{IDENT})\b(?P<body>[\s\S]*)",
                joined)
            if object_macro:
                found.append(Macro(object_macro["name"], (),
                                   object_macro["body"], first + 1, index + 1))
        index += 1
    return found


def balanced_arguments(source: str, opened: int) -> tuple[list[str], int] | None:
    """Parse an invocation; nested punctuation is allowed, literals refused."""
    depth = 1
    start = opened + 1
    args: list[str] = []
    for index in range(start, len(source)):
        char = source[index]
        if char in "\"'":
            return None
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                args.append(source[start:index].strip())
                return args, index + 1
        elif char == "," and depth == 1:
            args.append(source[start:index].strip())
            start = index + 1
    return None


def unsupported_guards_at(source: str, target_line: int) -> list[str]:
    """Refuse consumers inside conditionals other than a conventional guard."""
    lines = source.splitlines()
    guard = None
    for index, line in enumerate(lines[:8]):
        first = re.match(r"\s*#\s*ifndef\s+([A-Za-z_]\w*)\s*$", line)
        if first and any(re.match(rf"\s*#\s*define\s+{first.group(1)}\b", later)
                         for later in lines[index + 1:index + 4]):
            guard = first.group(1)
            break
    stack: list[str] = []
    for line in lines[:target_line]:
        directive = re.match(r"\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)", line)
        if not directive:
            continue
        kind, expression = directive.group(1), directive.group(2).strip()
        if kind in ("if", "ifdef", "ifndef"):
            stack.append(f"{kind} {expression}")
        elif kind == "elif" and stack:
            stack[-1] = f"elif {expression}"
        elif kind == "else" and stack:
            stack[-1] = "else"
        elif kind == "endif" and stack:
            stack.pop()
    return [value for value in stack if value != f"ifndef {guard}"]


def typed_consumers(source: str) -> tuple[list[dict], list[dict]]:
    """Find only accesses with an explicit struct type and literal field path."""
    clean = blank_comments(source)
    found: list[dict] = []
    refusals: list[dict] = []
    definitions = macros(clean)
    for macro in definitions:
        typed = TYPED_ACCESS.search(macro.body)
        if typed is None or typed["field_param"] not in macro.params:
            continue
        parameter = macro.params.index(typed["field_param"])
        # Keep other macros' invocations: the checked consumer often lives in
        # another macro, such as BKEY_FORMAT_CURRENT.
        masked = clean.splitlines(keepends=True)
        for line_number in range(macro.first_line - 1, macro.last_line):
            masked[line_number] = " " * len(masked[line_number])
        search_text = "".join(masked)
        for match in re.finditer(rf"\b{re.escape(macro.name)}\s*\(", search_text):
            opened = search_text.index("(", match.start(), match.end())
            parsed = balanced_arguments(search_text, opened)
            if parsed is None or len(parsed[0]) != len(macro.params):
                refusals.append({"macro": macro.name,
                                 "line": line_at(source, match.start()),
                                 "reason": "unsupported invocation syntax or arity"})
                continue
            field = parsed[0][parameter]
            if not LITERAL_PATH.fullmatch(field):
                refusals.append({"macro": macro.name,
                                 "line": line_at(source, match.start()),
                                 "reason": "field argument is not a literal member path"})
                continue
            invocation_line = line_at(source, match.start())
            enclosing = [other.name for other in definitions
                         if other.first_line <= invocation_line <= other.last_line
                         and other.name != macro.name]
            guards = sorted(set(unsupported_guards_at(source, macro.first_line)
                                + unsupported_guards_at(source, invocation_line)))
            if guards:
                refusals.append({"macro": macro.name, "line": invocation_line,
                                 "reason": "consumer is under an unproved preprocessor guard",
                                 "guards": guards})
                continue
            found.append({
                "struct": typed["type"], "field_path": field,
                "top_field": field.split(".")[0], "macro": macro.name,
                "macro_line": macro.first_line,
                "invocation_line": invocation_line,
                "enclosing_macro": enclosing[0] if len(enclosing) == 1 else None,
            })
    return found, refusals


def conditional_members(declaration: str, start_line: int) -> list[dict]:
    """Record direct struct fields under recognized byte-order branches.

    Unknown preprocessor conditions are recorded with no proven profile.
    This supplies evidence locations; the compiler decides actual validity.
    """
    active = {"little", "big"}
    stack: list[dict] = []
    result: list[dict] = []

    def byte_order_choice(expression: str) -> set[str]:
        for endian, order in (("little", "LITTLE"), ("big", "BIG")):
            if (re.search(rf"__BYTE_ORDER__\s*==\s*__ORDER_{order}_ENDIAN__",
                          expression)
                    or re.search(rf"defined\s*\(?\s*__{order}_ENDIAN_BITFIELD\b",
                                 expression)):
                return {endian}
        return set()

    for offset, line in enumerate(declaration.splitlines()):
        stripped = line.strip()
        directive = re.match(r"#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)", stripped)
        if directive:
            kind, expr = directive.group(1), directive.group(2)
            if kind in ("if", "ifdef", "ifndef"):
                chosen = byte_order_choice(expr) if kind == "if" else set()
                stack.append({"parent": active.copy(), "taken": chosen.copy(),
                              "unknown": not chosen})
                active &= chosen
            elif kind == "elif" and stack:
                frame = stack[-1]
                chosen = byte_order_choice(expr)
                active = (set() if frame["unknown"] else
                          frame["parent"] & (chosen - frame["taken"]))
                frame["taken"] |= chosen
                frame["unknown"] |= not chosen
            elif kind == "else" and stack:
                frame = stack[-1]
                active = (set() if frame["unknown"] else
                          frame["parent"] - frame["taken"])
                frame["taken"] = frame["parent"].copy()
            elif kind == "endif" and stack:
                active = stack.pop()["parent"]
            continue
        member = re.match(rf"\s*struct\s+(?P<type>{IDENT})\s+"
                          rf"(?P<name>{IDENT})\s*;", stripped)
        if member:
            result.append({"type": member["type"], "name": member["name"],
                           "line": start_line + offset,
                           "recognized_profiles": sorted(active)})
    return result


def probe_source(decls: dict, target: str, path: str, endian: str) -> tuple[str, list[str]]:
    if endian not in ("little", "big"):
        raise ValueError(f"unsupported endian profile: {endian}")
    closure = dependency_order(target, decls)
    expected = ("__ORDER_LITTLE_ENDIAN__" if endian == "little"
                else "__ORDER_BIG_ENDIAN__")
    prefix = f"""typedef unsigned char __u8;
typedef unsigned short __u16;
typedef unsigned int __u32;
typedef unsigned long long __u64;
#define __packed __attribute__((packed))
#define __aligned(n) __attribute__((aligned(n)))
#if __BYTE_ORDER__ != {expected}
#error compiler byte order is not the requested profile
#endif
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define __LITTLE_ENDIAN_BITFIELD 1
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
#define __BIG_ENDIAN_BITFIELD 1
#else
#error unsupported byte order
#endif
"""
    structs = "\n\n".join(decls[name].text for name in closure)
    accessor = (f"\nvoid check_field(void) {{ (void)(((const struct {target} *)0)"
                f"->{path}); }}\n")
    return prefix + structs + accessor, closure


def compile_access(code: str, compiler: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="field-consumer-") as directory:
        source = Path(directory) / "probe.c"
        source.write_text(code, encoding="utf-8")
        try:
            run = subprocess.run(
                [compiler, "-std=gnu11", "-fsyntax-only", "-Wall", "-Wextra",
                 "-Wno-packed-not-aligned", str(source)],
                text=True, capture_output=True, check=False)
        except OSError as error:
            return {"status": "insufficient", "reason":
                    f"toolchain unavailable: {error.__class__.__name__}",
                    "probe_sha256": digest(code)}
        diagnostic = run.stderr.replace(str(source), "<probe.c>").strip()
        error_lines = [line for line in diagnostic.splitlines() if "error:" in line]
        missing = [MISSING_MEMBER.search(line) for line in error_lines]
        if run.returncode == 0:
            status = "compiled"
        elif error_lines and all(missing) and len({m.group("member") for m in missing}) == 1:
            status = "missing_member"
        else:
            status = "insufficient"
        return {"status": status, "returncode": run.returncode,
                "missing_member": (missing[0].group("member")
                                   if status == "missing_member" else None),
                "diagnostic": diagnostic[-1800:], "probe_sha256": digest(code)}


def build_path_evidence(kconfig: str, makefile: str, fs_kconfig: str,
                        build_source: str, consumer_macro: str) -> dict:
    checks = {
        "config_symbol": (kconfig, r"(?m)^config\s+BCACHEFS_FS\b", "fs/bcachefs/Kconfig"),
        "config_dependency": (kconfig, r"(?m)^\s*depends on BLOCK\b", "fs/bcachefs/Kconfig"),
        "kconfig_source": (fs_kconfig, r'(?m)^source "fs/bcachefs/Kconfig"', "fs/Kconfig"),
        "makefile_gate": (makefile, r"obj-\$\(CONFIG_BCACHEFS_FS\)\s*\+=\s*bcachefs\.o", "fs/bcachefs/Makefile"),
        "object_list": (makefile, r"\bbkey\.o\b", "fs/bcachefs/Makefile"),
        "header_include": (build_source, r'(?m)^#include "bkey\.h"', "fs/bcachefs/bkey.c"),
        "consumer_use": (build_source, rf"\b{re.escape(consumer_macro)}\b", "fs/bcachefs/bkey.c"),
    }
    evidence = {}
    for name, (source, pattern, path) in checks.items():
        match = re.search(pattern, source)
        evidence[name] = ({"path": path, "line": line_at(source, match.start())}
                          if match else None)
    return {
        "status": ("static_build_path_found" if all(evidence.values())
                   else "unproved_static_build_path"),
        "checks": evidence,
        "limit": "No Kconfig solver, real .config, full kernel build, or runtime reachability proof",
    }


def analyze_one_revision(
    format_header: str, kconfig: str, makefile: str, fs_kconfig: str,
    build_source: str, *, revision: str, format_path: str,
    profiles: dict[str, tuple[str, str]],
) -> dict:
    decls = declarations(format_header)
    consumers, refused = typed_consumers(format_header)
    grouped: dict[tuple[str, str], dict] = {}
    for consumer in consumers:
        key = (consumer["struct"], consumer["field_path"])
        if key not in grouped:
            grouped[key] = {"struct": key[0], "field_path": key[1],
                            "top_field": consumer["top_field"],
                            "consumers": [], "profiles": {}}
        grouped[key]["consumers"].append(
            {k: consumer[k] for k in ("macro", "macro_line", "invocation_line",
                                      "enclosing_macro")})
    result = {
        "method": "one-revision typed-macro consumer field access compile check",
        "scope": ("C syntax review candidates only; the chosen typed-macro form, "
                  "not every consumer or interface obligation"),
        "source": {"revision": revision, "format_path": format_path,
                   "format_sha256": digest(format_header),
                   "kconfig_sha256": digest(kconfig),
                   "makefile_sha256": digest(makefile),
                   "fs_kconfig_sha256": digest(fs_kconfig),
                   "build_source_sha256": digest(build_source)},
        "profiles": {label: {"compiler": compiler, "endian": endian}
                     for label, (compiler, endian) in profiles.items()},
        "field_checks": [], "refused_consumers": refused,
    }
    for entry in grouped.values():
        decl = decls.get(entry["struct"])
        if decl is None:
            entry["classification"] = "insufficient"
            entry["reason"] = "target struct declaration absent from same header"
            result["field_checks"].append(entry)
            continue
        entry["declaration_line"] = decl.line
        entry["declaration_end_line"] = decl.end_line
        entry["direct_struct_members"] = conditional_members(decl.text, decl.line)
        for label, (compiler, endian) in profiles.items():
            try:
                code, closure = probe_source(decls, entry["struct"],
                                             entry["field_path"], endian)
                entry["source_closure"] = closure
                measurement = compile_access(code, compiler)
            except ValueError as error:
                measurement = {"status": "insufficient", "reason": str(error)}
            entry["profiles"][label] = measurement
        values = list(entry["profiles"].values())
        if not values or any(v["status"] == "insufficient" for v in values):
            entry["classification"] = "insufficient"
            entry["reason"] = "source closure or at least one compiler check unavailable"
        elif all(v["status"] == "compiled" for v in values):
            entry["classification"] = "normal_for_this_expression"
            entry["reason"] = "same-revision field expression compiles on both requested ABIs"
        elif (any(v["status"] == "compiled" for v in values)
              and any(v["status"] == "missing_member"
                      and v["missing_member"] == entry["top_field"] for v in values)):
            entry["classification"] = "candidate"
            entry["reason"] = "same consumer's top-level member is absent on one ABI"
        else:
            entry["classification"] = "insufficient"
            entry["reason"] = "compile results do not establish a shared-consumer mismatch"
        result["field_checks"].append(entry)
    # The typed macro may only be used inside another macro. The build source
    # must reference the outer expansion point for a static path to be found.
    macros_found = {c["enclosing_macro"] or c["macro"] for c in consumers}
    result["build_paths"] = {name: build_path_evidence(
        kconfig, makefile, fs_kconfig, build_source, name)
        for name in sorted(macros_found)}
    result["summary"] = {
        "candidate_paths": sum(x["classification"] == "candidate"
                               for x in result["field_checks"]),
        "normal_paths": sum(x["classification"] == "normal_for_this_expression"
                            for x in result["field_checks"]),
        "insufficient_paths": sum(x["classification"] == "insufficient"
                                  for x in result["field_checks"]),
        "refused_consumers": len(refused),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--little-cc", default="gcc")
    parser.add_argument("--big-cc", default="s390x-linux-gnu-gcc")
    args = parser.parse_args()
    commit = git_output(args.linux_dir, "rev-parse", f"{args.revision}^{{commit}}").strip()
    paths = {
        "format_header": "fs/bcachefs/bcachefs_format.h",
        "kconfig": "fs/bcachefs/Kconfig", "makefile": "fs/bcachefs/Makefile",
        "fs_kconfig": "fs/Kconfig", "build_source": "fs/bcachefs/bkey.c",
    }
    files = {key: git_output(args.linux_dir, "show", f"{commit}:{path}")
             for key, path in paths.items()}
    result = analyze_one_revision(
        **files, revision=commit, format_path=paths["format_header"],
        profiles={"x86_64_little": (args.little_cc, "little"),
                  "s390x_big": (args.big_cc, "big")})
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
