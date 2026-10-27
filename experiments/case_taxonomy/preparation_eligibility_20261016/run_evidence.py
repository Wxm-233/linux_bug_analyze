"""Replay complete known-source forward paths and lexical binding candidates."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.forward_guards import extract_forward_paths, indexed_field_candidates
from linux_bug_analyze.source_conditions import analyze_function


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    packet = json.loads((HERE / "source_material.json").read_text(encoding="utf-8-sig"))
    docs = {d["id"]: d for d in packet["documents"]}
    for document in docs.values():
        if hashlib.sha256(document["text"].encode()).hexdigest() != document["function_sha256"]:
            raise ValueError("Changed source: " + document["id"])
    maps = {name: extract_forward_paths(docs[name]) for name in ["old_s390_map", "fixed_s390_map"]}
    bindings = {name: indexed_field_candidates(docs[name]) for name in ["old_s390_update", "fixed_s390_update"]}
    starts = {name: analyze_function(docs[name]) for name in ["old_s390_start", "fixed_s390_start", "x86_callin", "common_notify", "common_starting"]}
    save(HERE / "forward_paths.json", maps)
    save(HERE / "binding_candidates.json", bindings)
    save(HERE / "entry_source_facts.json", starts)
    summary = {
        "schema": "preparation-eligibility-development-v1", "date": "2026-10-16",
        "case_scope": "already-read development case; no independent detection evaluation",
        "status": "bounded_source_facts_collected",
        "mapper_paths": {name: {"status": value["status"],
                                "terminal_paths": sum(p["status"] == "structural_terminal" for p in value["paths"]),
                                "frontier_paths": sum(p["status"] == "unsupported_frontier" for p in value["paths"]),
                                "paths": [{"guards": p["guards"], "status": p["status"],
                                           "standalone_calls": [e["callee"] for e in p["events"] if e["kind"] == "call"],
                                           "endpoint": p["endpoint"]} for p in value["paths"]]}
                         for name, value in maps.items()},
        "lexical_indexed_binding_candidates": {name: len(value) for name, value in bindings.items()},
        "binding_origin": "generic adjacent token pattern; iteration reachability and actual object identity unproved",
        "entry_function_status": {name: value["status"] for name, value in starts.items()},
        "whole_contract": "insufficient", "actual_consumption_content": "unknown",
        "new_kernel_runs": 0, "new_c_prototype_runs": 0, "new_defects": 0,
        "independent_detection_positives": 0,
        "method_versions": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            ROOT / "linux_bug_analyze/forward_guards.py", ROOT / "tests/test_forward_guards.py", Path(__file__).resolve()]},
    }
    save(HERE / "results.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
