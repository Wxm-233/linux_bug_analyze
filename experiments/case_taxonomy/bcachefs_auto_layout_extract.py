"""Locate conditional packed/aligned embedding contracts in two C headers.

This deliberately narrow prototype reads the same header at two Git revisions.
It selects *changed* struct declarations that are packed, explicitly aligned,
and contain byte-order conditionals; finds direct struct-member embeddings; and
measures the corresponding layout on two real compiler ABIs. A failed layout
predicate is a review candidate, never a vulnerability verdict. Unsupported C
syntax, missing source, or unavailable toolchains produces an explicit refusal.
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


STRUCT_START = re.compile(r"(?m)^[ \t]*struct[ \t]+([A-Za-z_]\w*)[ \t]*\{")
FIELD = re.compile(r"\bstruct[ \t]+([A-Za-z_]\w*)[ \t]+([A-Za-z_]\w*)[ \t]*(?:\[[^\]]*\])?[ \t]*;")
ALIGNED = re.compile(r"\b__aligned\s*\(\s*\d+\s*\)")
BYTE_ORDER = re.compile(r"__BYTE_ORDER__|__LITTLE_ENDIAN_BITFIELD|__BIG_ENDIAN_BITFIELD")
SCALAR_TYPES = {"__u8", "__u16", "__u32", "__u64", "__le16", "__le32", "__le64"}


@dataclass(frozen=True)
class Declaration:
    name: str
    start: int
    opened: int
    closed: int
    end: int
    text: str
    line: int
    end_line: int


def blank_comments(source: str) -> str:
    """Keep exact offsets and newlines while blanking comments and literals."""
    pattern = re.compile(r"/\*[\s\S]*?\*/|//[^\n]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")
    return pattern.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), source)


def line_at(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def declarations(source: str) -> dict[str, Declaration]:
    clean = blank_comments(source)
    found: dict[str, Declaration] = {}
    occupied_until = -1
    for match in STRUCT_START.finditer(clean):
        if match.start() < occupied_until:
            continue
        opened = clean.index("{", match.start(), match.end())
        depth = 0
        closed = None
        for offset in range(opened, len(clean)):
            if clean[offset] == "{":
                depth += 1
            elif clean[offset] == "}":
                depth -= 1
                if depth == 0:
                    closed = offset
                    break
        if closed is None:
            continue
        # An attribute may follow the closing brace, but arbitrary text does
        # not: the next semicolon terminates this C declaration.
        semi = clean.find(";", closed + 1)
        if semi < 0:
            continue
        end = semi + 1
        occupied_until = end
        found[match.group(1)] = Declaration(
            match.group(1), match.start(), opened, closed, end,
            source[match.start():end], line_at(source, match.start()),
            line_at(source, end - 1),
        )
    return found


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", blank_comments(text))


def has_contract_shape(decl: Declaration) -> bool:
    clean = blank_comments(decl.text)
    tail = clean[decl.closed - decl.start + 1:]
    return ("__packed" in tail and ALIGNED.search(tail) is not None
            and BYTE_ORDER.search(clean) is not None)


def embedding_sites(source: str, decls: dict[str, Declaration], target: str) -> list[dict]:
    clean = blank_comments(source)
    out = []
    for parent in decls.values():
        if parent.name == target:
            continue
        body = clean[parent.opened + 1:parent.closed]
        grouped: dict[str, list[int]] = {}
        for match in FIELD.finditer(body):
            if match.group(1) != target:
                continue
            field_offset = parent.opened + 1 + match.start()
            grouped.setdefault(match.group(2), []).append(line_at(source, field_offset))
        for field, lines in grouped.items():
            out.append({"parent": parent.name, "field": field,
                        "lines": lines, "parent_line": parent.line})
    return out


def dependency_order(parent: str, decls: dict[str, Declaration]) -> list[str]:
    """Return a compilable same-header closure or refuse unfamiliar syntax."""
    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in ordered:
            return
        if name in visiting:
            raise ValueError("recursive structure dependency")
        decl = decls.get(name)
        if decl is None:
            raise ValueError(f"struct {name} not defined in this header")
        clean = blank_comments(decl.text)
        body = clean[decl.opened - decl.start + 1:decl.closed - decl.start]
        if re.search(r"\bunion\b|\benum\b|\btypeof\b|\b__attribute__\b", body):
            raise ValueError(f"unsupported union/enum/attribute inside struct {name}")
        if re.search(r"\bstruct\s+\w+\s*\*", body):
            raise ValueError(f"pointer dependency inside struct {name} needs review")
        # Only known simple kernel scalar aliases may be stubbed; do not silently
        # invent layouts for UUIDs, atomics, or project-specific typedefs.
        tokens = set(re.findall(r"\b(?:__u\d+|__le\d+|u\d+|s\d+|uuid_t)\b", body))
        unknown = tokens - SCALAR_TYPES
        if unknown:
            raise ValueError(f"unsupported scalar alias in struct {name}: {sorted(unknown)}")
        visiting.add(name)
        for dep in re.findall(r"\bstruct\s+([A-Za-z_]\w*)\s+[A-Za-z_]\w*", body):
            if dep != name:
                visit(dep)
        visiting.remove(name)
        ordered.append(name)

    visit(parent)
    return ordered


def layout_c_source(decls: dict[str, Declaration], parent: str, member: str,
                    target: str) -> tuple[str, list[str]]:
    order = dependency_order(parent, decls)
    if target not in order:
        raise ValueError(f"{target} not present in dependency closure of {parent}")
    code = """#include <stddef.h>
#include <stdio.h>
typedef unsigned char __u8;
typedef unsigned short __u16;
typedef unsigned int __u32;
typedef unsigned long long __u64;
typedef __u16 __le16;
typedef __u32 __le32;
typedef __u64 __le64;
#define __packed __attribute__((packed))
#define __aligned(n) __attribute__((aligned(n)))
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define __LITTLE_ENDIAN_BITFIELD 1
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
#define __BIG_ENDIAN_BITFIELD 1
#else
#error unsupported byte order
#endif
"""
    code += "\n\n".join(decls[name].text for name in order)
    code += f"""
int main(void)
{{
    size_t alignment = _Alignof(struct {target});
    size_t offset = offsetof(struct {parent}, {member});
    printf("{{\\\"declared_alignment\\\":%zu,\\\"embedded_offset\\\":%zu,"
           "\\\"offset_meets_alignment\\\":%s,\\\"parent_size\\\":%zu}}\\n",
           alignment, offset, offset % alignment == 0 ? "true" : "false",
           sizeof(struct {parent}));
    return 0;
}}
"""
    return code, order


def measure(code: str, compiler: str, runner: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="bcachefs-auto-layout-") as temp:
        source = Path(temp) / "layout.c"
        binary = Path(temp) / "layout"
        source.write_text(code, encoding="utf-8")
        build = subprocess.run(
            [compiler, "-std=gnu11", "-O0", "-Wall", "-Wextra", str(source),
             "-o", str(binary)], text=True, capture_output=True, check=False)
        warnings = build.stderr.replace(str(source), "<probe.c>")
        if build.returncode != 0:
            return {"status": "insufficient", "reason": "compiler rejected source closure",
                    "diagnostic_excerpt": warnings[-2000:]}
        run = subprocess.run([*runner, str(binary)], text=True,
                             capture_output=True, check=False)
        if run.returncode != 0:
            return {"status": "insufficient", "reason": "compiled probe did not run",
                    "diagnostic_excerpt": run.stderr[-2000:]}
        try:
            value = json.loads(run.stdout)
        except json.JSONDecodeError:
            return {"status": "insufficient", "reason": "probe output is not JSON",
                    "diagnostic_excerpt": run.stdout[-500:]}
        # Warnings are saved as diagnostics, not elevated to defect verdicts.
        return {"status": "measured", "layout": value,
                "compiler_warnings": warnings.strip()}


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


def header_at(repo: Path, revision: str, path: str) -> tuple[str, str]:
    commit = git_output(repo, "rev-parse", f"{revision}^{{commit}}").strip()
    return commit, git_output(repo, "show", f"{commit}:{path}")


def analyze_texts(old: str, fixed: str, *, path: str, old_revision: str,
                  fixed_revision: str, profiles: dict[str, tuple[str, list[str]]]) -> dict:
    sources = {"old": old, "fixed": fixed}
    structs = {key: declarations(value) for key, value in sources.items()}
    result: dict = {
        "method": "changed conditional packed/aligned type + direct embedding + ABI layout measurement",
        "verdict_scope": "layout review candidates only; no vulnerability, reachability, or hardware verdict",
        "source": {"path": path, "old_revision": old_revision,
                   "fixed_revision": fixed_revision,
                   "sha256": {key: hashlib.sha256(value.encode()).hexdigest()
                              for key, value in sources.items()}},
        "profiles": list(profiles), "candidates": [], "excluded_unchanged": [],
    }
    for name, old_decl in structs["old"].items():
        new_decl = structs["fixed"].get(name)
        if new_decl is None or not (has_contract_shape(old_decl)
                                     or has_contract_shape(new_decl)):
            continue
        old_sites = {(entry["parent"], entry["field"]): entry for entry in
                     embedding_sites(old, structs["old"], name)}
        new_sites = {(entry["parent"], entry["field"]): entry for entry in
                     embedding_sites(fixed, structs["fixed"], name)}
        shared = sorted(set(old_sites) & set(new_sites))
        if normalized(old_decl.text) == normalized(new_decl.text):
            if shared:
                result["excluded_unchanged"].append({
                    "type": name, "old_line": old_decl.line,
                    "fixed_line": new_decl.line,
                    "reason": "declaration unchanged across revisions; warnings alone are not promoted",
                    "embedding_count": len(shared)})
            continue
        for parent, member in shared:
            entry = {
                "type": name, "embedded_in": parent, "field": member,
                "locations": {
                    "old": {"type_line": old_decl.line, "type_end_line": old_decl.end_line,
                            "field_lines": old_sites[(parent, member)]["lines"],
                            "parent_line": old_sites[(parent, member)]["parent_line"]},
                    "fixed": {"type_line": new_decl.line, "type_end_line": new_decl.end_line,
                              "field_lines": new_sites[(parent, member)]["lines"],
                              "parent_line": new_sites[(parent, member)]["parent_line"]},
                }, "measurements": {},
            }
            for revision in ("old", "fixed"):
                try:
                    code, order = layout_c_source(structs[revision], parent,
                                                   member, name)
                except ValueError as error:
                    entry["measurements"][revision] = {
                        profile: {"status": "insufficient", "reason": str(error)}
                        for profile in profiles}
                    continue
                entry.setdefault("source_closure", {})[revision] = order
                entry["measurements"][revision] = {}
                for profile, (compiler, runner) in profiles.items():
                    try:
                        value = measure(code, compiler, runner)
                    except OSError as error:
                        value = {"status": "insufficient", "reason":
                                 f"toolchain unavailable: {error.__class__.__name__}"}
                    entry["measurements"][revision][profile] = value
            values = [measurement for per_revision in entry["measurements"].values()
                      for measurement in per_revision.values()]
            if any(value["status"] != "measured" for value in values):
                entry["classification"] = "insufficient"
            else:
                old_bad = [p for p in profiles if not entry["measurements"]["old"][p]["layout"]["offset_meets_alignment"]]
                new_bad = [p for p in profiles if not entry["measurements"]["fixed"][p]["layout"]["offset_meets_alignment"]]
                entry["classification"] = (
                    "changed_layout_contract_candidate" if old_bad and not new_bad
                    else "normal_control" if not old_bad and not new_bad
                    else "unresolved_review")
                entry["old_inconsistent_profiles"] = old_bad
                entry["fixed_inconsistent_profiles"] = new_bad
            result["candidates"].append(entry)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--old-revision", required=True)
    parser.add_argument("--fixed-revision", required=True)
    parser.add_argument("--header", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--little-cc", default="gcc")
    parser.add_argument("--big-cc", default="s390x-linux-gnu-gcc")
    parser.add_argument("--big-runner", nargs="+",
                        default=["qemu-s390x", "-L", "/usr/s390x-linux-gnu"])
    args = parser.parse_args()
    old_id, old = header_at(args.linux_dir, args.old_revision, args.header)
    fixed_id, fixed = header_at(args.linux_dir, args.fixed_revision, args.header)
    outcome = analyze_texts(
        old, fixed, path=args.header, old_revision=old_id,
        fixed_revision=fixed_id,
        profiles={"x86_64_little": (args.little_cc, []),
                  "s390x_big": (args.big_cc, args.big_runner)})
    args.output.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"candidate_sites": len(outcome["candidates"]),
                      "classifications": [v["classification"] for v in outcome["candidates"]],
                      "excluded_unchanged": len(outcome["excluded_unchanged"])}))


if __name__ == "__main__":
    main()
