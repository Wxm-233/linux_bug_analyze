"""Find narrow endian-contract review leads from *one* Linux Git revision.

Only direct reads of ``__le16/__le32/__le64`` struct-pointer fields in ``if``
conditions are considered. The declaration must be present in the source or
a quoted local header reached within two include edges at the same revision.
This is a source triage aid, not a defect detector or a build/run validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
from collections import Counter, deque
from pathlib import Path


IDENT = r"[A-Za-z_]\w*"
REVISION = re.compile(r"[0-9a-fA-F]{7,40}\^?")
QUOTED_INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
STRUCT_OPEN = re.compile(rf"\bstruct\s+({IDENT})\s*\{{")
LE_FIELD = re.compile(rf"\b__le(16|32|64)\s+({IDENT})\s*;")
FUNCTION_OPEN = re.compile(rf"\b({IDENT})\s*\(([^;{{}}]*)\)\s*\{{", re.S)
POINTER_PARAM = re.compile(rf"\bstruct\s+({IDENT})\s*\*\s*({IDENT})\b")
CONTROL = {"if", "for", "while", "switch", "sizeof"}


def digest(contents: str) -> str:
    return hashlib.sha256(contents.encode("utf-8")).hexdigest()


def line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def mask_comments_and_literals(source: str) -> str:
    """Keep offsets and newlines while blanking comments and C literals."""
    chars = list(source)
    result = list(source)
    index = 0
    while index < len(chars):
        if source.startswith("//", index):
            end = source.find("\n", index)
            end = len(source) if end < 0 else end
            for pos in range(index, end):
                result[pos] = " "
            index = end
        elif source.startswith("/*", index):
            end = source.find("*/", index + 2)
            end = len(source) if end < 0 else end + 2
            for pos in range(index, end):
                if result[pos] != "\n":
                    result[pos] = " "
            index = end
        elif chars[index] in ('"', "'"):
            quote = chars[index]
            start = index
            index += 1
            while index < len(chars):
                if chars[index] == "\\":
                    index += 2
                elif chars[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            for pos in range(start, min(index, len(chars))):
                if result[pos] != "\n":
                    result[pos] = " "
        else:
            index += 1
    return "".join(result)


def closing_delimiter(masked: str, start: int, opening: str, closing: str) -> int | None:
    if start >= len(masked) or masked[start] != opening:
        return None
    depth = 0
    for index in range(start, len(masked)):
        if masked[index] == opening:
            depth += 1
        elif masked[index] == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def local_include_path(source_path: str, include: str) -> str | None:
    candidate = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), include))
    if candidate.startswith("../") or candidate.startswith("/") or candidate == "..":
        return None
    return candidate


def git_file(linux_dir: Path, revision: str, path: str) -> str | None:
    if not REVISION.fullmatch(revision):
        raise ValueError("revision must be a hexadecimal commit ID, optionally with ^")
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("source path must stay within the repository")
    process = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=linux_dir,
        capture_output=True, check=False,
    )
    if process.returncode:
        return None
    return process.stdout.decode("utf-8", errors="replace")


def source_tree(linux_dir: Path, revision: str, source_path: str,
                max_files: int = 64) -> tuple[dict[str, str], list[str]]:
    """Read source plus repository-local quoted includes, at depth <= 2."""
    pending = deque([(source_path, 0)])
    files: dict[str, str] = {}
    skipped: list[str] = []
    while pending:
        path, depth = pending.popleft()
        if path in files or path in skipped:
            continue
        if len(files) >= max_files:
            skipped.append(f"include limit {max_files} reached at {path}")
            continue
        contents = git_file(linux_dir, revision, path)
        if contents is None:
            skipped.append(f"unavailable at this revision: {path}")
            continue
        files[path] = contents
        if depth < 2:
            for match in QUOTED_INCLUDE.finditer(contents):
                included = local_include_path(path, match.group(1))
                if included is not None:
                    pending.append((included, depth + 1))
    return files, skipped


def typed_fields(files: dict[str, str]) -> dict[tuple[str, str], list[dict]]:
    fields: dict[tuple[str, str], list[dict]] = {}
    for path, source in files.items():
        clean = mask_comments_and_literals(source)
        for struct in STRUCT_OPEN.finditer(clean):
            opening = struct.end() - 1
            closing = closing_delimiter(clean, opening, "{", "}")
            if closing is None:
                continue
            body = clean[opening + 1:closing]
            # Only direct members. A matching member inside a nested union or
            # struct does not establish the type of `pointer->member`.
            depth = 1
            at_depth = [0] * len(body)
            for index, char in enumerate(body):
                at_depth[index] = depth
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
            for field in LE_FIELD.finditer(body):
                if at_depth[field.start()] != 1:
                    continue
                # Do not accept array declarators or pointer aliases.
                evidence = {
                    "struct": struct.group(1), "field": field.group(2),
                    "bits": int(field.group(1)), "file": path,
                    "line": line_number(source, opening + 1 + field.start()),
                }
                fields.setdefault((struct.group(1), field.group(2)), []).append(evidence)
    return fields


def classify_use(condition: str, access: re.Match[str], bits: int) -> tuple[str, str]:
    """Classify one direct read; no inference across aliases or macros."""
    exact = re.escape(access.group(0))
    conversion = rf"\ble{bits}_to_cpu\s*\(\s*{exact}\s*\)"
    if re.search(conversion, condition):
        return "normal", "explicit little-endian to CPU conversion at this read"
    mode = rf"\bS_IS(?:LNK|REG|DIR|CHR|BLK|FIFO|SOCK)\s*\(\s*{exact}\s*\)"
    if re.search(mode, condition):
        return "candidate", "little-endian mode passed directly to a host-mode test"
    before = condition[:access.start()]
    after = condition[access.end():]
    # A mask deliberately converted into the on-disk byte order is a valid
    # same-representation bitwise operation. Merely seeing `&` is insufficient.
    if (re.match(rf"\s*&(?!&)\s*cpu_to_le{bits}\s*\(", after)
            or re.search(rf"cpu_to_le{bits}\s*\([^()]*\)\s*&(?!&)\s*$", before)):
        return "normal", "bitmask operand converted to the same little-endian representation"
    if re.match(r"\s*\)*\s*&(?!&)", after) or re.search(r"(?<!&)&(?!&)\s*\(*\s*$", before):
        return "candidate", "little-endian value used directly as a bitmask operand"
    if re.match(r"\s*(?:==|!=)\s*0\b", after) or re.search(r"\b0\s*(?:==|!=)\s*$", before):
        return "normal", "comparison with zero is endian-invariant for this read"
    if re.fullmatch(r"\s*!?\s*" + exact + r"\s*", condition):
        return "normal", "zero/nonzero presence test is endian-invariant for this read"
    if (re.search(r"(?:^|&&|\|\||\()\s*!\s*$", before)
            and re.match(r"\s*(?:\)|&&|\|\||$)", after)):
        return "normal", "negated zero/nonzero test is endian-invariant for this read"
    if re.match(r"\s*(?:&&|\|\|)", after) and re.search(r"(?:^|[(&|!])\s*$", before):
        return "normal", "zero/nonzero presence test is endian-invariant for this read"
    return "insufficient", "expression use is outside the supported direct-read grammar"


def analyze_source(source_path: str, source: str,
                   fields: dict[tuple[str, str], list[dict]]) -> list[dict]:
    clean = mask_comments_and_literals(source)
    findings: list[dict] = []
    for function in FUNCTION_OPEN.finditer(clean):
        name = function.group(1)
        if name in CONTROL:
            continue
        opening = function.end() - 1
        closing = closing_delimiter(clean, opening, "{", "}")
        if closing is None:
            continue
        params = POINTER_PARAM.findall(function.group(2))
        mapped: dict[str, str] = {}
        for type_name, variable in params:
            mapped[variable] = type_name
        if not mapped:
            continue
        body = clean[opening + 1:closing]
        for if_match in re.finditer(r"\bif\s*\(", body):
            cond_open = opening + 1 + if_match.end() - 1
            cond_close = closing_delimiter(clean, cond_open, "(", ")")
            if cond_close is None or cond_close > closing:
                continue
            cond_clean = clean[cond_open + 1:cond_close]
            cond_source = source[cond_open + 1:cond_close]
            for variable, type_name in mapped.items():
                access_pattern = rf"\b{re.escape(variable)}\s*->\s*({IDENT})\b"
                for access in re.finditer(access_pattern, cond_clean):
                    field_name = access.group(1)
                    declaration = fields.get((type_name, field_name), [])
                    if not declaration:
                        # We cannot tell whether this is a native or an on-disk
                        # member, so no classification is made.
                        continue
                    if len(declaration) != 1:
                        status, reason = "insufficient", "multiple possible member declarations"
                    else:
                        status, reason = classify_use(cond_clean, access, declaration[0]["bits"])
                    findings.append({
                        "status": status, "reason": reason,
                        "function": name, "struct": type_name,
                        "field": field_name, "field_type": f"__le{declaration[0]['bits']}",
                        "source_file": source_path,
                        "source_line": line_number(source, cond_open + 1 + access.start()),
                        "condition": " ".join(cond_source.split()),
                        "declaration": declaration,
                    })
    return findings


def analyze_revision(linux_dir: Path, revision: str, source_path: str) -> dict:
    files, skipped = source_tree(linux_dir, revision, source_path)
    if source_path not in files:
        raise FileNotFoundError(f"source absent at revision {revision}: {source_path}")
    declarations = typed_fields(files)
    findings = analyze_source(source_path, files[source_path], declarations)
    counts = Counter(item["status"] for item in findings)
    return {
        "revision": revision, "source_file": source_path,
        "source_sha256": digest(files[source_path]),
        "files_read": [{"path": path, "sha256": digest(contents)}
                       for path, contents in files.items()],
        "include_notes": skipped,
        "findings": findings,
        "counts": {status: counts[status]
                   for status in ("candidate", "normal", "insufficient")},
        "scope": ("Only direct __le16/32/64 pointer-field reads in parseable if conditions; "
                  "normal applies to a read, not an entire function or revision. "
                  "Candidate means inspect, not a defect verdict."),
    }


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
