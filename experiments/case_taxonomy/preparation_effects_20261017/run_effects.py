"""Apply reviewed API summaries to source-bound known-case finite paths."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.forward_guards import extract_forward_paths
from linux_bug_analyze.finite_set_effects import interpret_set_trace, PREMISES


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_trace(path, registry):
    """Known-case operand projection, not an arbitrary pointer/alias analysis."""
    if path["status"] != "structural_terminal":
        return {"status": path["status"], "events": []}
    events, scratch_decl = [], None
    def operand(arg):
        nonlocal scratch_decl
        declaration = arg.get("declaration", {})
        if arg.get("binding") == "source_local_value_version" and arg.get("version") == "parameter":
            if declaration.get("parameter") == 0:
                return "dst"
            if declaration.get("parameter") == 1:
                return "target"
        if arg.get("binding") == "named_declaration_address_only" and declaration.get("storage") == ["static"]:
            if scratch_decl is None:
                scratch_decl = declaration
            if declaration == scratch_decl:
                return "scratch"
        raise ValueError("Operand cannot be mapped to the reviewed source parameter/declaration")
    for event in path["events"]:
        if event["kind"] == "forward_goto":
            continue
        if event["kind"] != "call" or event["callee"] not in registry:
            raise ValueError("Unreviewed path effect")
        summary = registry[event["callee"]]
        events.append({"summary": event["callee"], "definition_sha256": summary["definition_sha256"],
                       "args": [operand(arg) for arg in event["arguments"]],
                       "source_call": {"line": event["line"], "column": event["column"]}})
    return {"status": path["status"], "events": events,
            "binding_origin": "researcher_selected_parameter_roles_and_program_checked_source_declarations",
            "physical_pointer_identity": "not_proved"}


def main():
    material = read(HERE.parent / "preparation_eligibility_20261016/source_material.json")
    docs = {d["id"]: d for d in material["documents"]}
    primitives = read(HERE / "primitive_evidence.json")
    operation = {"cpumask_clear": "clear", "cpumask_set_cpu": "add", "cpumask_test_cpu": "test", "cpumask_copy": "copy"}
    # This registry was separately source-reviewed. Replaying changed evidence
    # must not manufacture a fresh semantic approval from an unchanged name.
    all_summaries, results = read(HERE / "primitive_summaries.json"), []
    for row in primitives["profiles"]:
        profile, revision = row["profile"], row["revision"]
        variant = profile.split("_")[0]
        doc = docs[variant + "_s390_map"]
        if doc["revision"] != revision or hashlib.sha256(doc["text"].encode()).hexdigest() != doc["function_sha256"]:
            raise ValueError("Changed/mismatched mapper source")
        context = {"profile": profile, "revision": revision,
                   "logical_bits": row["logical_bit_arguments"]["cpumask_clear"]}
        registry = all_summaries[profile]
        for name, effect in operation.items():
            definition = row["definitions"][name]
            if hashlib.sha256(definition["text"].encode()).hexdigest() != definition["sha256"]:
                raise ValueError("Primitive evidence changed")
            approved = registry[name]
            if (approved["definition_sha256"] != definition["sha256"] or approved["context"] != context
                    or approved["operation"] != effect or approved["review_origin"] != "researcher_review"):
                raise ValueError("Primitive differs from the separately reviewed summary; review again")
        paths = extract_forward_paths(doc)
        if len(paths["paths"]) != 3:
            raise ValueError("Known-case source paths differ; review before applying summaries")
        for index, path in enumerate(paths["paths"]):
            trace = source_trace(path, registry)
            common = {"objects": ["scratch", "dst"], "members": ["target"], "output": "dst", "target": "target"}
            actual = interpret_set_trace(trace, registry, context, **common)
            conditional = interpret_set_trace(trace, registry, context, assumptions=PREMISES, **common)
            results.append({"profile": profile, "revision": revision, "path_index": index,
                            "guard_alternatives": path["guards"], "path_status": path["status"],
                            "endpoint": path["endpoint"], "trace": trace,
                            "under_explicit_assumptions": conditional,
                            "without_proven_or_assumed_premises": actual,
                            "actual_branch_selected": "unknown", "consumer_deadline_content": "unknown"})
    summary = {"date": "2026-10-17", "status": "bounded_conditional_effect_review_completed",
               "case_scope": "one already-read development case; six path alternatives are not six cases",
               "conditional_postconditions": sum(r["under_explicit_assumptions"]["status"] == "conditional_postcondition" for r in results),
               "unsupported_conditional_paths": sum(r["under_explicit_assumptions"]["status"] == "insufficient" for r in results),
               "without_premises_insufficient": sum(r["without_proven_or_assumed_premises"]["status"] == "insufficient" for r in results),
               "results": results, "whole_contract": "insufficient", "runtime_effects_proved": False,
               "independent_positive_cases": 0, "independent_normal_cases": 0,
               "new_model_requests": 0, "new_builds": 0, "new_kernel_runs": 0, "new_defects": 0}
    if (summary["conditional_postconditions"], summary["unsupported_conditional_paths"], summary["without_premises_insufficient"]) != (4, 2, 6):
        raise ValueError("Conditional coverage differs; do not approve the result")
    save("results.json", summary)
    save("candidate_card.json", {
        "origin": "assistant_source_synthesis_with_independent_review; not automatic model inference",
        "base_card": "../state_contract_refine_20261015/contract_card.json",
        "base_card_modified": False,
        "provider_local_effect": "denial: logical output empty; accepted/non-HW: singleton target, conditional on reviewed API summaries and explicit premises",
        "provider_eligibility": "old online / fixed setup; never converted to consumer applicability",
        "compiled_field_and_symbol_binding": "../provider_consumer_binding_20261017/README.md",
        "updater_reaches_starting_target": "unknown", "final_link_or_runtime_address_identity": "unknown",
        "initial_common_use_and_stability": "unknown",
        "whole_contract": "insufficient", "automatic_requirements_adopted": 0,
        "next_action": "consolidate completed N1.4c evidence and unresolved obligations before any further same-case expansion"})
    print(json.dumps({k: summary[k] for k in ("status", "conditional_postconditions", "unsupported_conditional_paths",
                                             "without_premises_insufficient", "whole_contract")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
