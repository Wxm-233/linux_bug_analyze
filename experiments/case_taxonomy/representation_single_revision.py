"""Locate representation-layout review candidates from one historical C header.

Only the requested Git revision and header are read. The probe uses real
little-/big-endian compiler ABIs, but an offset/alignment mismatch is merely a
candidate for source review: deliberately packed formats can require one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from bcachefs_auto_layout_extract import (
    declarations,
    embedding_sites,
    has_contract_shape,
    header_at,
    layout_c_source,
    measure,
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def endian_guard(endian: str) -> str:
    if endian not in ("little", "big"):
        raise ValueError(f"unsupported endian profile: {endian}")
    expected = ("__ORDER_LITTLE_ENDIAN__" if endian == "little"
                else "__ORDER_BIG_ENDIAN__")
    return (f"#if __BYTE_ORDER__ != {expected}\n"
            "#error compiler does not match the requested endian profile\n"
            "#endif\n")


def analyze_single_header(
    header: str, *, path: str, revision: str,
    profiles: dict[str, tuple[str, list[str], str]],
) -> dict:
    """Scan one header, without knowing a later commit or changed declarations.

    Profiles map a label to (compiler, runner argv, expected endian). Every
    direct embedding receives a candidate/normal/insufficient classification.
    """
    structs = declarations(header)
    result = {
        "method": "one-revision conditional packed/aligned direct-embedding layout scan",
        "scope": ("review candidates only; a mismatch is not a defect verdict; "
                  "no build reachability, consumer semantics, or hardware test"),
        "source": {"revision": revision, "path": path,
                   "header_sha256": digest(header)},
        "profiles": {label: {"compiler": compiler, "expected_endian": endian,
                             "runner": runner}
                     for label, (compiler, runner, endian) in profiles.items()},
        "sites": [], "unembedded_types": [],
        "field_name_consistency": "not_checked",
    }
    for name, declaration in structs.items():
        if not has_contract_shape(declaration):
            continue
        sites = embedding_sites(header, structs, name)
        if not sites:
            result["unembedded_types"].append({
                "type": name, "type_line": declaration.line,
                "reason": "no direct named embedding in the same header"})
        for site in sites:
            entry = {
                "type": name,
                "type_line": declaration.line,
                "type_end_line": declaration.end_line,
                "embedded_in": site["parent"],
                "parent_line": site["parent_line"],
                "field": site["field"],
                "field_lines": site["lines"],
                "measurements": {},
            }
            try:
                code, closure = layout_c_source(
                    structs, site["parent"], site["field"], name)
                entry["source_closure"] = closure
            except ValueError as error:
                entry["classification"] = "insufficient"
                entry["reason"] = str(error)
                result["sites"].append(entry)
                continue

            for label, (compiler, runner, endian) in profiles.items():
                try:
                    guarded_code = endian_guard(endian) + code
                    value = measure(guarded_code, compiler, runner)
                    value["probe_sha256"] = digest(guarded_code)
                except OSError as error:
                    value = {"status": "insufficient",
                             "reason": f"toolchain unavailable: {error.__class__.__name__}"}
                entry["measurements"][label] = value
            if not profiles or any(v["status"] != "measured"
                                   for v in entry["measurements"].values()):
                entry["classification"] = "insufficient"
                entry["reason"] = "one or more requested ABI measurements unavailable"
            else:
                bad = [label for label, value in entry["measurements"].items()
                       if not value["layout"]["offset_meets_alignment"]]
                entry["classification"] = "candidate" if bad else "normal"
                entry["alignment_review_profiles"] = bad
                if bad:
                    entry["reason"] = ("embedded offset is not a multiple of the "
                                       "declared member type alignment; inspect packed "
                                       "format intent and consumers")
                else:
                    entry["reason"] = "measured offsets satisfy this narrow predicate"
            result["sites"].append(entry)
    result["summary"] = {
        state: sum(entry["classification"] == state for entry in result["sites"])
        for state in ("candidate", "normal", "insufficient")
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--header", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--little-cc", default="gcc")
    parser.add_argument("--big-cc", default="s390x-linux-gnu-gcc")
    parser.add_argument("--big-runner", nargs="+",
                        default=["qemu-s390x", "-L", "/usr/s390x-linux-gnu"])
    args = parser.parse_args()
    revision, header = header_at(args.linux_dir, args.revision, args.header)
    outcome = analyze_single_header(
        header, path=args.header, revision=revision,
        profiles={"x86_64_little": (args.little_cc, [], "little"),
                  "s390x_big": (args.big_cc, args.big_runner, "big")})
    args.output.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(outcome["summary"]))


if __name__ == "__main__":
    main()
