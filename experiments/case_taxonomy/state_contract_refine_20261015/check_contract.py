"""Evaluate a researcher-reviewed, narrow known-case contract, not arbitrary C.

Inputs are explicit evidence records. Reference bounds and recorded logical values
can be checked mechanically; source meaning, effective paths and real observations
must be reviewed separately. There is intentionally no whole-kernel PASS result.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path


STAGE = Path(__file__).resolve().parent
REPO = STAGE.parents[2]
ALLOWED_ORIGINS = {
    "researcher_source_inference", "reviewed_configuration_projection",
    "reviewed_archived_observation", "mock_assumption",
}
REQUIRED_PREMISES = (
    "interface_identity", "target_argument_binding", "provider_binding",
    "common_consumer_deadline", "effective_path", "observation_object_binding",
)
REQUIRED_REFERENCE_GROUPS = (
    "interface_identity", "common_deadline", "consumer_read_and_leader",
    "initial_rq_binding", "x86_provider_and_preparation",
    "s390_provider_and_eligibility", "s390_initialization_scope", "effective_configuration",
)
REQUIRED_CONFIGURATION = {
    "common": ["SMP", "SCHED_SMT", "SCHED_CORE"], "s390": ["SCHED_TOPOLOGY"], "x86": [],
}


def source_index():
    packet = json.loads((STAGE.parent / "state_context_binding_20261015/source_packet.json").read_text(encoding="utf-8-sig"))
    additions = json.loads((STAGE.parent / "claude_contract_resume_20261015/source_additions.json").read_text(encoding="utf-8-sig"))
    documents = packet["original_source_request"]["documents"] + packet["supplemental_documents"] + additions["documents"]
    return {doc["id"]: doc for doc in documents}, packet["revision"]


def validate_card(card):
    """Validate recorded references and declared scope, never source semantics."""
    errors = []
    docs, revision = source_index()
    if card.get("schema_version") != 2 or card.get("origin") != "researcher_synthesis":
        errors.append("card is not the reviewed researcher schema")
    if card.get("revision") != revision:
        errors.append("card/source revision mismatch")
    authority = card.get("authority", {})
    if authority.get("kind") != "conditional_necessary_candidate" or authority.get("sufficient_for_correctness") is not False:
        errors.append("authority must remain conditional and non-sufficient")
    if card.get("predicate") != {"operator": "set_contains", "container": "target_smt_group", "member": "target_cpu"}:
        errors.append("unsupported predicate")
    if card.get("reviewed_binding", {}).get("exact_consumption_observation") != "unknown":
        errors.append("this version has no reviewed exact-consumption observation")
    for group, names in REQUIRED_CONFIGURATION.items():
        if card.get("required_configuration", {}).get(group) != names:
            errors.append("unsupported configuration scope: " + group)
    refs = card.get("source_references", {})
    for group in REQUIRED_REFERENCE_GROUPS:
        if not refs.get(group):
            errors.append("missing reference group: " + group)
    for group, references in refs.items():
        for ref in references:
            doc = docs.get(ref.get("document"))
            start, end = ref.get("start_line"), ref.get("end_line")
            if not doc or type(start) is not int or type(end) is not int:
                errors.append("unknown/malformed reference: " + group)
            elif not doc["start_line"] <= start <= end <= doc["end_line"]:
                errors.append("out-of-range reference: " + group)
            elif ref.get("path") != doc["path"]:
                errors.append("reference path mismatch: " + group)
    for position in card.get("positions", []):
        if "document" in position:
            doc, line = docs.get(position["document"]), position.get("line")
            if not doc or type(line) is not int or not doc["start_line"] <= line <= doc["end_line"]:
                errors.append("out-of-range position: " + position.get("id", "unknown"))
    return errors


def supported(record):
    return (
        isinstance(record, dict)
        and record.get("status") == "supported"
        and record.get("origin") in ALLOWED_ORIGINS
        and isinstance(record.get("evidence"), str)
        and bool(record["evidence"].strip())
    )


def configuration_value(name, record):
    """Recognize an explicit projection, without running or inferring Kconfig."""
    if not supported(record) or type(record.get("value")) is not bool:
        return None
    raw = record.get("raw", "").strip()
    expected = "CONFIG_" + name + "=y" if record["value"] else "# CONFIG_" + name + " is not set"
    return record["value"] if raw == expected else None


def evaluate(card, observation):
    result = {
        "id": observation.get("id"),
        "scope": "insufficient", "relation": "insufficient", "observation_tier": "none",
        "at_exact_consumption": "insufficient", "whole_path": "insufficient",
        "warning_is_oracle": False, "reasons": [], "companion_conditions": {},
        "provenance": {
            "card_origin": card.get("origin"),
            "input_origin": observation.get("origin"),
            "independent_case": False,
        },
    }
    invalid = validate_card(card)
    if invalid:
        result["reasons"] = invalid
        return result
    arch = observation.get("architecture")
    if arch not in card["architecture_fulfillment"]:
        result["reasons"].append("architecture/provider not reviewed; absence is not inapplicability")
        return result
    required = card["required_configuration"]["common"] + card["required_configuration"].get(arch, [])
    states = {name: configuration_value(name, observation.get("configuration", {}).get(name)) for name in required}
    disabled = [name for name, state in states.items() if state is False]
    if disabled:
        result.update(scope="not_applicable", relation="not_applicable", at_exact_consumption="not_applicable")
        result["reasons"].append("explicitly disabled for this selected contract: " + ", ".join(disabled))
        result["reasons"].append("a fallback/other consumer path requires a separate applicability review")
        return result
    missing = ["configuration:" + name for name, state in states.items() if state is None]
    premises = observation.get("premises", {})
    missing += [name for name in REQUIRED_PREMISES if not supported(premises.get(name))]
    if missing:
        result["reasons"].append("missing reviewed premises: " + ", ".join(missing))
        return result
    result["scope"] = "conditional_applicable"
    if observation.get("position") != "observed_sample":
        result["reasons"].append("this card only binds a separate sample; pointer acquisition is not content use and exact-consumption binding is unknown")
        return result
    target, bits, width = observation.get("target_cpu"), observation.get("mask_bits"), observation.get("cpu_bound")
    if any(type(value) is not int for value in [target, bits, width]) or not 0 <= target < width <= 4096 or bits < 0 or bits >= 1 << width:
        result["reasons"].append("invalid/missing target, finite CPU bound or mask value")
        return result
    result["observation_tier"] = "observed_sample"
    result["relation"] = "satisfied_narrow" if bits & (1 << target) else "violated_narrow"
    result["reasons"].append("membership is evaluated only at the declared sample, conditional on reviewed interface identity")
    core = observation.get("initial_core_by_cpu")
    initial_supported = supported(premises.get("initial_rq_values"))
    if initial_supported and isinstance(core, list) and len(core) == width and all(type(value) is int and 0 <= value < width for value in core):
        result["companion_conditions"]["target_initially_self"] = "satisfied" if core[target] == target else "violated"
        others = [cpu for cpu in range(width) if cpu != target and bits & (1 << cpu) and core[cpu] == cpu]
        result["companion_conditions"]["other_self_leader"] = (
            "not_required_by_singleton_branch" if bits.bit_count() == 1 else "satisfied" if others else "violated"
        )
        result["companion_conditions"]["eligible_other_leaders"] = others
    else:
        result["companion_conditions"].update(target_initially_self="insufficient", other_self_leader="insufficient")
    result["reasons"].append("exact iteration values, full group consistency, intervening writers and concurrent correctness remain unproved")
    return result


def mock_observation(case, architecture="s390"):
    """Declare logical-harness assumptions explicitly; no archived boot is replayed."""
    assumption = {"status": "supported", "origin": "mock_assumption", "evidence": "constructed local harness assumption, not a hardware reachability claim"}
    names = ["SMP", "SCHED_SMT", "SCHED_CORE"] + (["SCHED_TOPOLOGY"] if architecture == "s390" else [])
    return {
        "id": case["id"], "origin": "existing_mock_logical_input", "architecture": architecture,
        "position": "observed_sample", "target_cpu": case["target_cpu"], "cpu_bound": len(case["initial_core_by_cpu"]),
        "mask_bits": case["mask_bits"], "initial_core_by_cpu": list(case["initial_core_by_cpu"]),
        "warning_lines": case["warn_source_lines"],
        "premises": {name: copy.deepcopy(assumption) for name in REQUIRED_PREMISES + ("initial_rq_values",)},
        "configuration": {name: {**assumption, "value": True, "raw": "CONFIG_" + name + "=y"} for name in names},
    }


def replay_recorded_vectors(card):
    probe_path = STAGE.parent / "claude_contract_resume_20261015/probe_results.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8-sig"))
    if probe["source_revision"] != card["revision"]:
        raise ValueError("recorded probe and card revisions differ")
    rows = []
    for case in probe["cases"]:
        evaluated = evaluate(card, mock_observation(case))
        evaluated["recorded_warning_lines"] = case["warn_source_lines"]
        evaluated["recorded_target_core_cpu"] = case["target_core_cpu"]
        rows.append(evaluated)
    return {
        "schema": "conditional_contract_recorded_vector_replay_v1", "date": "2026-10-15",
        "card_origin": "researcher_synthesis", "model_candidate_adopted": False,
        "input": "../claude_contract_resume_20261015/probe_results.json", "results": rows,
        "counts": {"recorded_logical_inputs": len(rows), "new_c_executions": 0, "new_kernel_runs": 0, "new_cases": 0},
        "limits": "Only declared mock assumptions and recorded values are evaluated. No new hardware, reachability, exact-event, concurrency or independent-generalization evidence.",
    }


if __name__ == "__main__":
    card = json.loads((STAGE / "contract_card.json").read_text(encoding="utf-8-sig"))
    errors = validate_card(card)
    if errors:
        raise SystemExit(json.dumps({"errors": errors}))
    report = replay_recorded_vectors(card)
    (STAGE / "gate_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "recorded_vectors_evaluated", "counts": report["counts"], "whole_path_pass_claims": 0}))
