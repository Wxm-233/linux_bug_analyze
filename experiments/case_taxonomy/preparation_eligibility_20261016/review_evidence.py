"""Offline known-case review: reuse existing extractors; no model or kernel run.

This checks local structural evidence and records unresolved links. It does not
approve semantic claims, resolve cross-TU symbols, or infer helper effects.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.forward_guards import extract_forward_paths, indexed_field_candidates
from linux_bug_analyze.source_conditions import analyze_function
from linux_bug_analyze.contract_protocol import ContractError, validate_contract, CLAIM_ROLES

spec = importlib.util.spec_from_file_location(
    "known_source_queries", HERE.parent / "source_conditions_20261016/run_evidence.py")
queries = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queries)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    docs = {d["id"]: d for d in read(HERE / "source_material.json")["documents"]}
    for doc in docs.values():
        if hashlib.sha256(doc["text"].encode()).hexdigest() != doc["function_sha256"]:
            raise ValueError("Changed original source: " + doc["id"])
    facts = {name: analyze_function(docs[name]) for name in (
        "old_s390_start", "fixed_s390_start", "x86_callin", "common_starting")}
    selected = [
        ("old_s390_start", "old.update_before_notify", "update_cpu_masks", "notify_cpu_starting", None),
        ("fixed_s390_start", "fixed.update_before_notify", "update_cpu_masks", "notify_cpu_starting", None),
        ("fixed_s390_start", "fixed.setup_before_update", "cpumask_set_cpu", "update_cpu_masks", None),
        ("fixed_s390_start", "fixed.setup_before_notify", "cpumask_set_cpu", "notify_cpu_starting", 0),
        ("old_s390_start", "old.notify_before_online", "notify_cpu_starting", "set_cpu_online", 0),
        ("fixed_s390_start", "fixed.notify_before_online", "notify_cpu_starting", "set_cpu_online", 0),
        ("x86_callin", "x86.map_before_notify", "set_cpu_sibling_map", "notify_cpu_starting", 0),
        ("common_starting", "common.core_before_rq", "sched_core_cpu_starting", "sched_rq_cpu_starting", 0),
    ]
    local = [queries.local_query(facts[d], name, a, b, arg) for d, name, a, b, arg in selected]
    paths, bindings, configured = {}, {}, {}
    for variant in ("old", "fixed"):
        mapped = extract_forward_paths(docs[variant + "_s390_map"])
        candidates = indexed_field_candidates(docs[variant + "_s390_update"])
        profile = read(HERE.parent / "consumer_preprocessing_20261016" / (variant + "_s390.json"))
        getter = profile["functions"]["cpu_smt_mask"]
        if (profile["profile"] != variant + "_s390" or profile["arch"] != "s390"
                or profile["variant"] != variant
                or profile["revision"] != docs[variant + "_s390_map"]["revision"]):
            raise ValueError("Configured getter profile/revision differs")
        if hashlib.sha256(getter["text"].encode()).hexdigest() != getter["sha256"]:
            raise ValueError("Configured getter changed")
        paths[variant] = [{"guards": p["guards"], "status": p["status"],
                           "calls": [e["callee"] for e in p["events"] if e["kind"] == "call"],
                           "endpoint": p["endpoint"]} for p in mapped["paths"]]
        bindings[variant] = candidates
        configured[variant] = {
            "profile": profile["profile"], "revision": profile["revision"],
            "effective_config": profile["effective_config"],
            "getter_text": getter["text"], "getter_source": getter["name_location"],
            "getter_sha256": getter["sha256"],
            "field_spelling_matches_candidate": bool(len(candidates) == 1 and
                (candidates[0]["indexed_base_spelling"] + "[" + candidates[0]["index_spelling"] +
                 "]." + candidates[0]["member_spelling"]) in getter["text"].replace(" ", "")),
            "cross_translation_unit_symbol_identity": "not_proved_by_this_spelling_check",
            "target_reached_in_updater_iteration": "unknown",
        }

    # Existing core must reject using a runtime provider guard as configuration
    # scope. This is a schema negative control, not an automatically inferred rule.
    bad_scope = {
        "schema": "architecture_contract_v1", "id": "negative.provider_scope",
        "revision": "synthetic-negative-control", "authority_kind": "consumer_inferred",
        "sufficient_for_correctness": False,
        "symbols": {"active": {"type": "bool", "role": "configuration"},
                    "eligible": {"type": "bool", "role": "observation"}},
        "required_claims": {role: role for role in CLAIM_ROLES},
        "field_origins": {k: "researcher_authored" for k in
                          ("scope", "relation", "symbols", "required_claims", "authority_kind")},
        "scope": {"op": "and", "args": [{"symbol": "active"}, {"symbol": "eligible"}]},
        "relation": {"symbol": "eligible"},
    }
    try:
        validate_contract(bad_scope)
    except ContractError as error:
        rejected_scope, scope_reason = True, str(error)
    else:
        rejected_scope, scope_reason = False, "unexpectedly accepted"
    negative = {
        "runtime_eligibility_in_configuration_scope_rejected": rejected_scope,
        "scope_rejection_reason": scope_reason,
        "no_cross_function_object_proof_from_candidate": all(
            c["object_identity_proved"] is False and c["iteration_reaches_target"] == "unknown"
            for rows in bindings.values() for c in rows) and all(len(v) == 1 for v in bindings.values()),
        "hw_frontier_never_promoted_to_copy_or_completion": all(
            len([p for p in rows if p["status"] == "unsupported_frontier"]) == 1 and
            all("cpumask_copy" not in p["calls"] for p in rows if p["status"] == "unsupported_frontier")
            for rows in paths.values()),
        "scope_limit": "Cannot reject a semantic mislabel as configuration by syntax alone; external review remains necessary.",
    }
    expected = ["not_established"] + ["verified_local_structure"] * 7
    observed = [q["status"] for q in local]
    if observed != expected or not all(negative[k] for k in (
        "runtime_eligibility_in_configuration_scope_rejected",
        "no_cross_function_object_proof_from_candidate",
        "hw_frontier_never_promoted_to_copy_or_completion")):
        raise ValueError("Review expectations failed; do not approve the candidate chain")
    result = {
        "schema": "preparation-review-evidence-v1", "date": "2026-10-16",
        "status": "limited_source_review_completed",
        "origin": "researcher_selected_known_case_queries_checked_by_existing_programs",
        "local_queries": local, "mapper_paths": paths,
        "field_candidates": bindings, "configured_getters": configured,
        "negative_controls": negative, "whole_contract": "insufficient",
        "helper_effects": "not_automatically_proved", "deadline_content": "unknown",
        "semantic_review_file": "semantic_review.md",
        "model_analysis_complete": False, "model_requirements_automatically_adopted": 0,
        "new_model_requests": 0, "new_builds": 0, "new_kernel_runs": 0,
        "new_defects": 0, "independent_positive_cases": 0, "independent_normal_cases": 0,
    }
    (HERE / "semantic_review_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"local_queries": len(local), "statuses": observed,
                      "negative_controls": negative, "whole_contract": result["whole_contract"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
