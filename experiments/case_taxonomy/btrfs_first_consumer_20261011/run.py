"""One fixed-material run plus six preregistered semantic-boundary checks.

Review and freeze both code files in code_identity.json before running. Run
with stdout/stderr redirected to first_stdout.txt / first_stderr.txt. This
runner has no command-line knobs and never imports a historic harness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from extractor import extract_facts


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FUNCTIONS = ("open_ctree", "btrfs_parse_options")  # Manual function selection.
FIXED_PAIRS = [
    ("before", "analysis_out/boundary-contracts-20260915-v2/btrfs/before/fs_btrfs_disk-io.c",
     "analysis_out/boundary-contracts-20260915-v2/btrfs/before/fs_btrfs_super.c"),
    ("after", "analysis_out/boundary-contracts-20260915-v2/btrfs/after/fs_btrfs_disk-io.c",
     "analysis_out/boundary-contracts-20260915-v2/btrfs/after/fs_btrfs_super.c"),
]
CONSUMER = "int consume(struct sample *input) { return input->unit; }\n"
SYNTHETIC = {
    "late_source": ("int __cold launch(void) { struct sample *p; unsigned value; consume(p); value = fetch(); p->unit = value; return 0; }\n", CONSUMER),
    "early_source": ("int __attribute__((cold)) launch(void) { struct sample *p; p->unit = fetch(); consume(p); return 0; }\n", CONSUMER),
    "comment_string_decoys": ('''/* int launch(void) { consume(q); q->unit = fake(); } */
int launch(void) {
    struct sample *p;
    char *decoy = "consume(q); p->unit = fake(); }";
    // consume(q); p->unit = fake();
    p->unit = fetch();
    consume(p);
    return 0;
}
''', CONSUMER),
    "other_object": ("int launch(void) { struct sample *p; struct sample *q; q->unit = fetch(); consume(p); return 0; }\n", CONSUMER),
    "reassigned_parameter": ("int launch(void) { struct sample *p; p->unit = fetch(); consume(p); return 0; }\n",
                             "int consume(struct sample *input) { ((input)) = other(); return input->unit; }\n"),
    "conditional_source": ("int launch(void) { struct sample *p; if (flag) { p->unit = fetch(); } consume(p); return 0; }\n", CONSUMER),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def verify_identity() -> dict:
    identity = read_json("code_identity.json")
    entries = identity["files"]
    if {entry["path"] for entry in entries} != {"extractor.py", "run.py"} or len(entries) != 2:
        raise ValueError("code_identity.json must identify exactly extractor.py and run.py")
    for entry in entries:
        if sha256((HERE / entry["path"]).read_bytes()) != entry["sha256"]:
            raise ValueError("reviewed code identity mismatch: " + entry["path"])
    return identity


def check_source(result: dict, expected: dict) -> dict:
    matches = [r for r in result["records"] if r["field"] == expected["expected_field"]]
    checks = {
        "limited_facts": result["status"] == "limited_facts",
        "one_expected_field_candidate": len(matches) == 1,
    }
    if len(matches) == 1:
        record = matches[0]
        local = record["local_assignment"]
        checks.update({
            "relation": record["relation"] == expected["expected_relation"],
            "source_local_line": local is not None and local["line"] == expected["source_local_line"],
            "source_field_write_line": record["field_write"]["line"] == expected["source_field_write_line"],
            "consumer_call_line": record["consumer_call"]["line"] == expected["consumer_call_line"],
            "consumer_field_read_line": record["consumer_first_field_read_line"] == expected["consumer_field_read_line"],
        })
    return {"checks": checks, "passed": all(checks.values()), "interpretation": "Development-source shape check; not a blind accuracy or defect result."}


def check_boundary(result: dict, expected: dict) -> dict:
    checks = {"record_count": len(result["records"]) == expected["expected_records"]}
    if "expected_status" in expected:
        checks["status"] = result["status"] == expected["expected_status"]
    else:
        checks["status"] = result["status"] == "limited_facts"
    if "expected_relation" in expected:
        checks["relation"] = all(r["relation"] == expected["expected_relation"] for r in result["records"])
    checks["CFG_and_success_unproven"] = {"CFG_dominance", "true_path_reachability", "consumer_call_return_and_success"}.issubset(result["unproven"])
    checks["lexical_only_records"] = all(r["evidence_status"] == "lexical_candidate" for r in result["records"])
    return {"checks": checks, "passed": all(checks.values())}


def main() -> int:
    if len(sys.argv) != 1:
        raise ValueError("This fixed-scope runner accepts no arguments")
    if (HERE / "results.json").exists():
        raise ValueError("results.json already exists; preserve the first run instead of overwriting it")
    identity = verify_identity()
    materials = read_json("materials_pre.json")
    expectations = read_json("expectations_pre.json")
    fixed_paths = {path for _, caller, consumer in FIXED_PAIRS for path in (caller, consumer)}
    metadata = {m["path"]: m for m in materials["materials"]}
    if set(metadata) != fixed_paths or len(materials["materials"]) != 4:
        raise ValueError("materials must identify exactly the four fixed C sources")
    if sha256((HERE / "protocol_pre.md").read_bytes()) != materials["protocol_sha256"]:
        raise ValueError("preregistered protocol identity mismatch")
    sources = {}
    total_bytes = 0
    for path in sorted(fixed_paths):
        data = (ROOT / path).read_bytes()
        total_bytes += len(data)
        if total_bytes > 512 * 1024:
            raise ValueError("source read limit exceeded")
        if len(data) != metadata[path]["bytes"] or sha256(data) != metadata[path]["sha256"]:
            raise ValueError("fixed source identity mismatch: " + path)
        sources[path] = data.decode("utf-8")
    if total_bytes != materials["total_bytes"]:
        raise ValueError("material byte total mismatch")
    source_expectations = {item["source_pair"]: item for item in expectations["source_expectations"]}
    boundary_expectations = {item["id"]: item for item in expectations["synthetic_boundary_expectations"]}
    if set(source_expectations) != {pair[0] for pair in FIXED_PAIRS} or set(boundary_expectations) != set(SYNTHETIC):
        raise ValueError("preregistered expectations do not match the fixed run scope")
    output = {
        "scope": "Known-case limited lexical supplement; no new independent positive or mount test.",
        "code_identity": identity,
        "material_total_bytes": total_bytes,
        "manual_function_selection": list(FUNCTIONS),
        "always_unproven": expectations["always_unproven"],
        "source_pairs": [], "synthetic_boundaries": [],
    }
    passed = True
    for label, caller_path, consumer_path in FIXED_PAIRS:
        facts = extract_facts(sources[caller_path], sources[consumer_path], *FUNCTIONS)
        validation = check_source(facts, source_expectations[label])
        output["source_pairs"].append({"source_pair": label, "caller_path": caller_path,
                                       "consumer_path": consumer_path, "facts": facts, "validation": validation})
        passed = passed and validation["passed"]
        print(label + ": " + facts["status"] + ", " + str(len(facts["records"])) + " intersecting lexical candidate(s); checks=" + str(validation["passed"]))
    for name, (caller, consumer) in SYNTHETIC.items():
        facts = extract_facts(caller, consumer, "launch", "consume")
        validation = check_boundary(facts, boundary_expectations[name])
        output["synthetic_boundaries"].append({"id": name, "facts": facts, "validation": validation})
        passed = passed and validation["passed"]
        print(name + ": " + facts["status"] + ", " + str(len(facts["records"])) + " candidate(s); checks=" + str(validation["passed"]))
    output["all_preregistered_checks_passed"] = passed
    (HERE / "results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("results.json saved; CFG, external effects, format semantics, and actual execution remain unproven.")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        print("runner stopped: " + str(error), file=sys.stderr)
        sys.exit(2)
