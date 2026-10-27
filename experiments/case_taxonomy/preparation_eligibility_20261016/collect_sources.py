"""Collect a bounded set of already-read original Git functions; no execution."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


STAGE = Path(__file__).resolve().parent
IMPORTED_PACKET = STAGE.parent / "source_conditions_20261016" / "source_functions.json"
REPOSITORY = "/root/repos/linux"
OLD = "88b604263f3d6eedae0b1c2c3bbd602d1e2e8775"
FIXED = "a052096bdd6809eeab809202726634d1ac975aa1"


def git_file(revision: str, path: str) -> bytes:
    command = ["git", "-C", REPOSITORY, "show", f"{revision}:{path}"]
    if os.name == "nt":
        command = ["wsl.exe", "-d", "Ubuntu", "--", *command]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Cannot read original Git object {revision}:{path}")
    return result.stdout


def lexical_mask(text: str) -> str:
    """Mask comments and literals while retaining source positions/newlines."""
    pattern = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    return pattern.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), text)


def complete_function(raw: bytes, name: str, definition_index: int | None = None) -> tuple[int, int, str]:
    text = raw.decode("utf-8")
    masked = lexical_mask(text)
    # This collector supports the ordinary scalar-return declarations used by
    # the named functions below. It is not a general C declaration parser.
    declaration = re.compile(
        rf"(?m)^[ \t]*(?:(?:static|inline|__always_inline|__init)\s+)*"
        rf"(?:void|int|bool|unsigned\s+int)\s+{re.escape(name)}\s*\("
    )
    matches = []
    for match in declaration.finditer(masked):
        position = match.end() - 1
        depth = 0
        for position in range(position, len(masked)):
            if masked[position] == "(":
                depth += 1
            elif masked[position] == ")":
                depth -= 1
                if depth == 0:
                    break
        else:
            continue
        position += 1
        while position < len(masked) and masked[position].isspace():
            position += 1
        if position >= len(masked) or masked[position] != "{":
            continue
        depth = 0
        for closing in range(position, len(masked)):
            if masked[closing] == "{":
                depth += 1
            elif masked[closing] == "}":
                depth -= 1
                if depth == 0:
                    first = text.count("\n", 0, match.start()) + 1
                    last = text.count("\n", 0, closing) + 1
                    lines = text.splitlines(keepends=True)
                    fragment = "".join(lines[first - 1:last])
                    matches.append((first, last, fragment))
                    break
    if definition_index is not None:
        if definition_index < 0 or definition_index >= len(matches):
            raise ValueError(f"Definition index out of range for {name}")
        return matches[definition_index]
    if len(matches) != 1:
        raise ValueError(f"Expected one complete supported definition of {name}, found {len(matches)}")
    return matches[0]


def build_material() -> dict:
    cache: dict[tuple[str, str], bytes] = {}

    def collect(identifier: str, revision: str, path: str, function: str, definition_index: int | None = None) -> dict:
        key = (revision, path)
        if key not in cache:
            cache[key] = git_file(*key)
        raw = cache[key]
        first, last, fragment = complete_function(raw, function, definition_index)
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        return {
            "id": identifier,
            "kind": "source",
            "source": "local_git_object_original_uninstrumented",
            "revision": revision,
            "path": path,
            "function": function,
            "start_line": first,
            "end_line": last,
            "text": fragment,
            "git_blob": git_blob,
            "full_file_sha256": hashlib.sha256(raw).hexdigest(),
            "function_sha256": hashlib.sha256(fragment.encode("utf-8")).hexdigest(),
            "scope_note": "Complete original function text; not a configured translation unit, reachability proof or semantic oracle.",
        }

    imported = json.loads(IMPORTED_PACKET.read_text(encoding="utf-8"))
    documents = []
    for existing in imported["documents"]:
        document = collect(existing["id"], existing["revision"], existing["path"], existing["function"])
        if (document["start_line"], document["end_line"]) != (existing["start_line"], existing["end_line"]):
            raise ValueError(f"Imported source range differs from original Git: {existing['id']}")
        if document["text"].rstrip("\r\n") != existing["text"].rstrip("\r\n"):
            raise ValueError(f"Imported source text differs from original Git: {existing['id']}")
        document["imported_from"] = {
            "path": "../source_conditions_20261016/source_functions.json",
            "id": existing["id"],
            "function_sha256": existing["function_sha256"],
            "verification": "same original range/text; trailing newline count normalized by Git line slice",
        }
        documents.append(document)

    for prefix, revision in [("old", OLD), ("fixed", FIXED)]:
        documents.append(collect(f"{prefix}_s390_update", revision, "arch/s390/kernel/topology.c", "update_cpu_masks"))
        for name in ["cpumask_clear", "cpumask_copy", "cpumask_test_cpu"]:
            documents.append(collect(f"{prefix}_helper_{name}", revision, "include/linux/cpumask.h", name))
        header_lines = cache[(revision, "include/linux/cpumask.h")].decode("utf-8").splitlines()
        opening = [i + 1 for i, line in enumerate(header_lines) if line.strip() == "#if NR_CPUS > 1"]
        closing = [i + 1 for i, line in enumerate(header_lines) if line.strip() == "#endif /* NR_CPUS > 1 */"]
        if len(opening) != 1 or len(closing) != 1:
            raise ValueError("Expected the bounded original NR_CPUS guard")
        alternatives = [i + 1 for i in range(opening[0], closing[0] - 1) if header_lines[i].strip() == "#else"]
        if len(alternatives) != 1:
            raise ValueError("Expected one bounded NR_CPUS alternative")
        for index, suffix in [(0, "nr_cpus_gt1"), (1, "nr_cpus_else")]:
            document = collect(f"{prefix}_helper_cpu_online_{suffix}", revision, "include/linux/cpumask.h", "cpu_online", index)
            if index == 0 and not opening[0] < document["start_line"] < alternatives[0]:
                raise ValueError("cpu_online first definition outside expected original branch")
            if index == 1 and not alternatives[0] < document["start_line"] < closing[0]:
                raise ValueError("cpu_online second definition outside expected original branch")
            document["preprocessor_context"] = {
                "selection": "first branch" if index == 0 else "else branch",
                "not_evaluated": True,
                "references": [
                    {"line": line, "text": header_lines[line - 1]}
                    for line in [opening[0], alternatives[0], closing[0]]
                ],
                "scope": "Exact nearby original directives; not a preprocessed/configuration evaluation.",
            }
            documents.append(document)

    if len({d["id"] for d in documents}) != len(documents):
        raise ValueError("Duplicate document IDs")
    return {
        "schema": "preparation_eligibility_known_source_material_v1",
        "date": "2026-10-16",
        "purpose": "Already-read s390/x86 development source material for bounded forward eligibility/object/notification review.",
        "repository": REPOSITORY,
        "revisions": [OLD, FIXED],
        "imported_packet": "../source_conditions_20261016/source_functions.json",
        "documents": documents,
        "collection_notes": [
            "Initial collection stopped before output on two cpu_online definitions; both original NR_CPUS branches are now retained explicitly with directive references."
        ],
        "limits": [
            "Original Git source only; no fresh model/API, compilation, execution or new candidate.",
            "Different revisions retain distinct document IDs even where function text is identical.",
            "Function bodies are not preprocessed; adjacent preprocessor guards and all configuration constraints are outside these function slices.",
            "Helper text is supporting source, not an implemented effect model or permission to infer semantic readiness.",
            "The updater's local loop CPU is not bound to the starting CPU by name; target membership/reachability and same-object facts require separate review.",
            "No runtime oracle, self predicate, expected classification or all-writer/concurrency proof is supplied.",
        ],
    }


if __name__ == "__main__":
    material = build_material()
    destination = STAGE / "source_material.json"
    destination.write_text(json.dumps(material, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "collected_original_git", "documents": len(material["documents"]), "output": str(destination)}, ensure_ascii=False))
