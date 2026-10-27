"""Replay local source evidence; optionally check an archived model final.

This script performs no network calls or kernel execution. Researcher-selected
queries are labelled separately from unchanged model claims and AST-derived facts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.source_conditions import analyze_function, check_source_claim


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def local_query(analysis, name, first_name, target_name, argument_index=None):
    """Select known-case queries by name, but derive their source anchors."""
    claim = {"id": name, "document": analysis["document"],
             "revision": analysis["revision"], "function": analysis["function"],
             "kind": "before"}
    for field, callee in (("first", first_name), ("target", target_name)):
        choices = [c for c in analysis["calls"] if c["callee"] == callee]
        if len(choices) != 1:
            raise ValueError(f"Query {name}: no unique {callee} anchor")
        call = choices[0]
        claim[field] = {k: call[k] for k in ("callee", "line", "column", "arguments")}
    if argument_index is not None:
        claim["argument_index"] = argument_index
    checked = check_source_claim(analysis, claim)
    checked["query_origin"] = "researcher_selected_known_case_question"
    checked["anchor_origin"] = "program_derived_from_source_AST"
    return checked


def parse_final(raw):
    text = raw.strip()
    fence = re.fullmatch(r"```json\s*\n([\s\S]*)\n```", text)
    if fence:
        text = fence[1]
    value = json.loads(text)  # No substring extraction, field repair or retries.
    if not isinstance(value, dict) or value.get("schema") != "source-claims-v1":
        raise ValueError("Wrong model final schema")
    claims = value.get("claims")
    if not isinstance(claims, list) or len(claims) > 3 or not all(isinstance(c, dict) for c in claims):
        raise ValueError("Invalid model claims collection")
    return value, bool(fence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-directory", type=Path,
                        help="Existing ignored model archive; writes checks alongside its final.md")
    args = parser.parse_args()
    documents = read_json(STAGE / "source_functions.json")["documents"]
    analyses = {}
    for document in documents:
        actual = hashlib.sha256(document["text"].encode()).hexdigest()
        if actual != document["function_sha256"]:
            raise ValueError("Changed source function: " + document["id"])
        analyses[document["id"]] = analyze_function(document, annotations=("__init",))
    save(STAGE / "source_facts.json", {"schema": "source-condition-facts-v1", "functions": analyses})

    queries = [
        ("old_s390_start", "old.update_before_notify", "update_cpu_masks", "notify_cpu_starting", None),
        ("fixed_s390_start", "fixed.update_before_notify", "update_cpu_masks", "notify_cpu_starting", None),
        ("fixed_s390_start", "fixed.setup_before_notify", "cpumask_set_cpu", "notify_cpu_starting", 0),
        ("x86_callin", "x86.map_before_notify", "set_cpu_sibling_map", "notify_cpu_starting", 0),
        ("common_starting", "common.core_before_rq", "sched_core_cpu_starting", "sched_rq_cpu_starting", 0),
    ]
    selected = [local_query(analyses[doc], name, first, target, index)
                for doc, name, first, target, index in queries]
    save(STAGE / "selected_query_results.json", selected)

    model = {"status": "not_requested", "new_request": False}
    if args.model_directory:
        directory = args.model_directory.resolve()
        archive_root = (ROOT.parent / "模型调用测试").resolve()
        if not directory.is_relative_to(archive_root):
            raise ValueError("Model material/checks must remain inside the ignored model archive")
        final = directory / "final.md"
        try:
            value, outer_fence = parse_final(final.read_text(encoding="utf-8-sig"))
            checked = [check_source_claim(analyses.get(c.get("document"), {}), c)
                       for c in value["claims"]]
            model = {"status": "checked_unchanged_claims", "new_request": False,
                     "final_sha256": digest(final), "outer_json_fence_removed": outer_fence,
                     "claim_count": len(checked),
                     "claims": [{"id": c["claim_id"], "status": c["status"],
                                 "whole_contract": c["whole_contract"]} for c in checked],
                     "semantic_requirement_count": len(value.get("semantic_requirements", [])),
                     "semantic_requirements_auto_adopted": 0}
            save(directory / "source_claim_checks.json", {
                "schema": "model-source-claim-checks-v1", "summary": model,
                "checks": checked, "semantic_requirements_status": "separate_manual_review_required"})
        except (ValueError, KeyError, TypeError) as error:
            model = {"status": "format_failure_preserved", "new_request": False,
                     "error": str(error), "final_sha256": digest(final)}
            save(directory / "source_claim_checks.json", model)

    old_versions = read_json(STAGE.parent / "contract_protocol_20261016/results.json")["version_files"]
    unchanged = {name: digest(ROOT / Path(name.replace("\\", "/"))) == sha
                 for name, sha in old_versions.items()}
    summary = {
        "schema": "source-conditions-development-v1", "date": "2026-10-16",
        "purpose": "Known-case development; no independent detection evaluation",
        "source_functions": len(analyses),
        "supported_local_flow": sum(a["status"] == "bounded_local_flow" for a in analyses.values()),
        "insufficient_flow": sum(a["status"] == "insufficient" for a in analyses.values()),
        "function_status": {k: {"status": a["status"], "path_count": len(a["paths"]),
                                "reasons": a["reasons"]} for k, a in analyses.items()},
        "selected_queries": [{"id": q["claim_id"], "status": q["status"],
                              "object_identity": q["object_identity"]} for q in selected],
        "model_check": model, "previous_protocol_files_unchanged": unchanged,
        "whole_contract": "insufficient", "semantic_requirements_automatically_validated": 0,
        "new_kernel_runs": 0, "independent_defect_detections": 0,
        "version_files": {str(p.relative_to(ROOT)): digest(p) for p in (
            ROOT / "linux_bug_analyze/source_conditions.py",
            ROOT / "tests/test_source_conditions.py", Path(__file__).resolve(),
            STAGE / "source_functions.json")},
    }
    save(STAGE / "results.json", summary)
    print(json.dumps({k: summary[k] for k in ("source_functions", "supported_local_flow",
                     "insufficient_flow", "selected_queries", "model_check",
                     "previous_protocol_files_unchanged")}, ensure_ascii=False))
    return 0 if all(unchanged.values()) and model["status"] != "format_failure_preserved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
