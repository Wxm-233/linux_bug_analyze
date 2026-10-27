"""Compile a source-review-driven bkey field-access probe on two endiannesses.

This is a narrow historical source comparison, not a Linux kernel build. The
three declarations are copied verbatim from each Git revision; only scalar
aliases and attribute macros are stubbed so the C compiler can type-check a
single `k->bversion.lo` access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


FIX = "2007d28ec0095c6db0a24fd8bb8fe280c65446cd"
HEADER = "fs/bcachefs/bcachefs_format.h"
NAMES = ("bpos", "bversion", "bkey")


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git_text(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *arguments],
                                   text=True, encoding="utf-8")


def blank_comments(source: str) -> str:
    """Keep offsets stable while making punctuation inside comments inert."""
    pattern = re.compile(r"/\*[\s\S]*?\*/|//[^\n]*")
    return pattern.sub(lambda match: re.sub(r"[^\n]", " ", match.group()), source)


def struct_declaration(header: str, name: str) -> dict:
    clean = blank_comments(header)
    start_match = re.search(rf"(?m)^struct {re.escape(name)} \{{", clean)
    if start_match is None:
        raise ValueError(f"missing struct {name}")
    opened = clean.index("{", start_match.start())
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
        raise ValueError(f"unterminated struct {name}")
    end = clean.index(";", closed) + 1
    fragment = header[start_match.start():end]
    return {"text": fragment, "line": header.count("\n", 0, start_match.start()) + 1,
            "end_line": header.count("\n", 0, end - 1) + 1,
            "sha256": sha256(fragment)}


def c_probe(declarations: dict[str, dict], *, endian: str) -> str:
    if endian not in ("little", "big"):
        raise ValueError(endian)
    order = "__ORDER_LITTLE_ENDIAN__" if endian == "little" else "__ORDER_BIG_ENDIAN__"
    prefix = f"""/* Historical declarations follow without member edits. */
typedef unsigned char __u8;
typedef unsigned int __u32;
typedef unsigned long long __u64;
#define __packed __attribute__((packed))
#define __aligned(n) __attribute__((aligned(n)))
#if __BYTE_ORDER__ != {order}
#error compiler does not match the requested endian profile
#endif
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define __LITTLE_ENDIAN_BITFIELD 1
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
#define __BIG_ENDIAN_BITFIELD 1
#else
#error unsupported byte order
#endif
"""
    return prefix + "\n\n".join(declarations[name]["text"] for name in NAMES) + """

/* The field access is the entire checked behavior. */
__u64 bkey_bversion_lo(const struct bkey *key)
{
    return key->bversion.lo;
}
"""


def compile_only(code: str, compiler: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="bcachefs-field-name-") as temp:
        c_path = Path(temp) / "field.c"
        obj_path = Path(temp) / "field.o"
        c_path.write_text(code, encoding="utf-8")
        command = [compiler, "-std=gnu11", "-Wall", "-Wextra",
                   "-Wno-packed-not-aligned", "-c", str(c_path), "-o", str(obj_path)]
        try:
            completed = subprocess.run(command, text=True, encoding="utf-8",
                                       capture_output=True, check=False)
        except OSError as error:
            return {"status": "toolchain_unavailable", "reason": str(error),
                    "probe_sha256": sha256(code)}
        return {
            "status": "compiled" if completed.returncode == 0 else "compile_failed",
            "returncode": completed.returncode,
            "diagnostic": completed.stderr.replace(str(c_path), "<historical-probe.c>").strip(),
            "stdout": completed.stdout.strip(),
            "object_created": obj_path.is_file(),
            "probe_sha256": sha256(code),
        }


def run(repo: Path) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    profiles = {"x86_64_little": ("gcc", "little"),
                "s390x_big": ("s390x-linux-gnu-gcc", "big")}
    results = {}
    for label, revision in (("parent", FIX + "^"), ("fixed", FIX)):
        commit = git_text(repo, "rev-parse", f"{revision}^{{commit}}").strip()
        header = git_text(repo, "show", f"{commit}:{HEADER}")
        declarations = {name: struct_declaration(header, name) for name in NAMES}
        results[label] = {
            "commit": commit, "header_sha256": sha256(header),
            "declarations": {name: {key: value for key, value in declaration.items()
                                     if key != "text"}
                             for name, declaration in declarations.items()},
            "profiles": {},
        }
        for profile, (compiler, endian) in profiles.items():
            result = compile_only(c_probe(declarations, endian=endian), compiler)
            result["compiler"] = compiler
            result["expected_endian"] = endian
            results[label]["profiles"][profile] = result
    return {
        "method": "post-source-review directed C member-access compile check",
        "scope": "three verbatim historical structs plus scalar/attribute stubs; no kernel build or Rust binding",
        "source_path": HEADER,
        "checked_expression": "key->bversion.lo",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "revisions": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.linux_dir)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({revision: {profile: record["status"]
                                for profile, record in item["profiles"].items()}
                      for revision, item in result["revisions"].items()}))


if __name__ == "__main__":
    main()
