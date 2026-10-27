"""Adapt five already-read synthetic vectors; never run a kernel or model."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from linux_bug_analyze.contract_protocol import CLAIM_ROLES, SCHEMA, evaluate_contract


def run():
    previous_path = HERE.parent / "state_contract_refine_20261015/check_contract.py"
    spec = importlib.util.spec_from_file_location("reviewed_known_case", previous_path)
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    card = json.loads(previous_path.with_name("contract_card.json").read_text(encoding="utf-8-sig"))
    if previous.validate_card(card):
        raise ValueError("Previous reviewed card is not valid in its original scope")
    docs, revision = previous.source_index()
    probe_path = HERE.parent / "claude_contract_resume_20261015/probe_results.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8-sig"))
    if probe["source_revision"] != revision:
        raise ValueError("Archived vector revision mismatch")

    contract = {
        "schema": SCHEMA, "id": "known.group.membership", "revision": revision,
        "authority_kind": "consumer_inferred", "sufficient_for_correctness": False,
        "field_origins": {key: "researcher_authored" for key in
                          ("scope", "relation", "symbols", "required_claims", "authority_kind")},
        "required_claims": {role: "known." + role for role in CLAIM_ROLES},
        "symbols": {"selected_path": {"type": "bool", "role": "configuration"},
                    "provided_group": {"type": "int_set", "role": "observation"},
                    "selected_member": {"type": "int", "role": "observation"}},
        "scope": {"symbol": "selected_path"},
        "relation": {"op": "contains", "args": [{"symbol": "provided_group"}, {"symbol": "selected_member"}]},
    }
    groups = {
        "authority": "interface_identity", "interface": "interface_identity",
        "consumer_requirement": "consumer_read_and_leader", "provider_binding": "s390_provider_and_eligibility",
        "object_binding": "initial_rq_binding", "deadline_binding": "common_deadline",
        "applicability": "effective_configuration",
    }
    base = {
        "revision": revision, "basis": "synthetic", "claims": {},
        "contract_id": contract["id"], "field_origins": copy.deepcopy(contract["field_origins"]),
        "documents": {name: {"context_revision": revision, "path": doc["path"],
                      "start_line": doc["start_line"], "end_line": doc["end_line"]} for name, doc in docs.items()},
    }
    for role, group in groups.items():
        base["claims"]["known." + role] = {
            "role": role, "status": "supported", "origin": "researcher_review",
            "statement": "Reviewed known-case premise from the prior card; not an independently derived rule.",
            "references": [{key: ref[key] for key in ("document", "start_line", "end_line")}
                           for ref in card["source_references"][group]],
        }
    base["claims"]["known.authority"]["authority_kind"] = "consumer_inferred"
    base["claims"]["known.authority"]["supports_requirement"] = "known.consumer_requirement"
    for role, expression in (("applicability", "scope"), ("consumer_requirement", "relation")):
        base["claims"]["known." + role].update(expression=copy.deepcopy(contract[expression]),
                                               symbols=copy.deepcopy(contract["symbols"]))
    base["documents"]["vectors"] = {
        "context_revision": revision, "path": str(probe_path.relative_to(REPO)),
        "start_line": 1, "end_line": len(probe_path.read_text(encoding="utf-8-sig").splitlines()),
    }
    refs = [{"document": "vectors", "start_line": 1, "end_line": base["documents"]["vectors"]["end_line"]}]
    results = []
    for row in probe["cases"]:
        context, obj = "mock:" + row["id"], "cpu:" + str(row["target_cpu"])
        ledger = copy.deepcopy(base)
        ledger["context_id"] = context
        for role in ("consumer_requirement", "provider_binding", "object_binding", "deadline_binding"):
            ledger["claims"]["known." + role]["object_id"] = obj
        ledger["claims"]["known.deadline_binding"].update(event_id="first_content_use", event_kind="content_consumption")
        binding = {"context_id": context, "object_id": obj, "event_id": "separate_sample",
                   "deadline_id": "first_content_use", "event_kind": "sample"}
        ledger["claims"]["known.observation"] = {
            "role": "observation_binding", "status": "supported", "origin": "synthetic_assumption",
            "statement": "Explicit synthetic value binding; no real consumption snapshot or reachability claim.",
            "references": refs, "binding": binding,
        }
        record = {
            "id": row["id"], "revision": revision, "basis": "synthetic", "context_id": context,
            "object_id": obj, "sample_event": "separate_sample", "sample_kind": "sample",
            "deadline_event": "first_content_use", "observation_binding": {**binding, "claim": "known.observation"},
            "facts": {},
        }
        values = {
            "selected_path": True,
            "provided_group": [cpu for cpu in range(len(row["initial_core_by_cpu"])) if row["mask_bits"] & (1 << cpu)],
            "selected_member": row["target_cpu"],
        }
        for name, value in values.items():
            role = contract["symbols"][name]["role"]
            projected = {"symbol": name, "value": value, "role": role, "context_id": context}
            fact = {"value": value, "claim": "value." + name}
            if role == "observation":
                projected.update(object_id=obj, event_id="separate_sample")
                fact.update(object_id=obj, event_id="separate_sample")
            ledger["claims"]["value." + name] = {
                "role": "fact", "status": "supported", "origin": "synthetic_assumption",
                "statement": "Archived constructed input; selected_path is an assumption, not new Kconfig evidence.",
                "references": refs, "fact": projected,
            }
            record["facts"][name] = fact
        for claim in ledger["claims"].values():
            claim["context_id"] = context
        result = evaluate_contract(contract, ledger, record, allow_synthetic=True)
        old = previous.evaluate(card, previous.mock_observation(row))
        expected = {"satisfied_narrow": "satisfied", "violated_narrow": "violated"}[old["relation"]]
        if result["relation_at_observation"] != expected:
            raise AssertionError((row["id"], result))
        if result["relation_at_deadline"] != "insufficient" or result["whole_path"] != "insufficient":
            raise AssertionError("Synthetic separate sample was promoted")
        result["previous_narrow_relation"] = old["relation"]
        results.append(result)
    core = REPO / "linux_bug_analyze/contract_protocol.py"
    test = REPO / "tests/test_contract_protocol.py"
    return {
        "schema": "contract_protocol_known_replay_v1", "date": "2026-10-16", "contract": contract,
        "status": "bounded_compatibility_pass", "results": results,
        "counts": {"already_recorded_synthetic_inputs": len(results), "new_kernel_runs": 0,
                   "new_c_executions": 0, "new_model_requests": 0, "new_defects": 0,
                   "qualified_independent_positive": 0, "qualified_independent_normal": 0},
        "version_files": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (core, test, Path(__file__).resolve())},
        "limits": "Manual known-case adapter and externally reviewed premises. This proves neither extraction, independent transfer, runtime deadline satisfaction nor novelty.",
    }


if __name__ == "__main__":
    report = run()
    (HERE / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "counts": report["counts"]}))
