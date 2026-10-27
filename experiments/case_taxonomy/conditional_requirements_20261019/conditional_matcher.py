"""Compare reviewed symbolic guarantees only; never report an actual defect.

Reviews/roles/summaries are explicit researcher inputs, not inferred authority.
This module neither reads reference files nor verifies their semantic content.
The caller binds the archived inputs. Qualification is not consumer applicability.
"""
from copy import deepcopy
import re

REQUIRED_PREMISES = (
    "distinct_nonoverlapping_storage", "equal_logical_domains", "legal_member_indices",
    "no_interference_during_trace", "source_bound_selected_trace",
    "summarized_calls_return_normally", "valid_storage",
)
CONTEXT_KEYS = {"profile", "revision", "config_sha256", "basis"}
KINDS = {"target_membership", "search_witness", "post_update_consistency"}


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {"unknown", "none", "?"}


def _review(review):
    if not isinstance(review, dict) or review.get("status") != "supported" or review.get("origin") != "researcher_review": return False
    refs = review.get("references")
    return isinstance(refs, list) and bool(refs) and all(
        _text(ref) if isinstance(ref, str) else isinstance(ref, dict) and any(_text(ref.get(key)) for key in ("artifact", "file", "path"))
        for ref in refs)


def _context(context):
    return (isinstance(context, dict) and set(context) == CONTEXT_KEYS and _text(context.get("profile"))
            and isinstance(context.get("revision"), str) and re.fullmatch(r"[0-9a-f]{40}", context["revision"]) is not None
            and isinstance(context.get("config_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", context["config_sha256"]) is not None
            and context.get("basis") == "noninstrumented_static")


def _guards(guards):
    if not isinstance(guards, list) or not guards: return False
    for guard in guards:
        if not isinstance(guard, dict) or not _text(guard.get("expression")) or type(guard.get("taken")) is not bool: return False
        if any(key in guard and (type(guard[key]) is not int or guard[key] < 1) for key in ("line", "column")): return False
    return True


def compare_guarantee(requirement, effect, context):
    """Return a conditional property comparison, with all runtime claims open.

    `postcondition=[]` is a complete empty set when completeness is explicit.
    Exact role/context and reviewed purpose are mandatory. The search summary
    must explicitly state cardinality, same complete iteration domain, singleton
    bypass and a reviewed witness-before-update continuation goal. Cardinality
    is usable only with explicit no-bits-outside-iteration and mask/nr_cpu_ids
    stability conditions. These are unproved premises, not observed invariants.
    The goal is not a proof that this invocation must continue.
    No field/core relation solver is implemented in this scope.
    """
    result = {
        "status": "insufficient", "actual_verdict": "insufficient", "whole_contract": "insufficient",
        "consumer_applicability": "not_decided", "qualification_status": "not_evaluated",
        "applicability_scope": "conditional_property_only", "context": deepcopy(context),
        "requirement_id": requirement.get("id") if isinstance(requirement, dict) else None,
        "kind": requirement.get("kind") if isinstance(requirement, dict) else None,
        "condition_guards": [], "reasons": [], "premises_proved": False, "runtime_effects_proved": False,
        "unproved_premises": list(REQUIRED_PREMISES) + [
            "symbolic_roles_correspond_to_consumer", "reviewed_consumer_purpose_applies",
            "actual_provider_path_selected", "same_runtime_target_and_object",
            "preparation_reaches_consumer_deadline", "content_stable_until_consumption",
        ],
    }
    def stop(reason):
        result["reasons"].append(reason)
        return result
    if not isinstance(requirement, dict) or not isinstance(effect, dict): return stop("malformed_requirement_or_effect")
    if not _context(context): return stop("unsupported_or_incomplete_context")
    if not _context(requirement.get("context")) or requirement["context"] != context: return stop("requirement_context_mismatch")
    if not _context(effect.get("context")) or effect["context"] != context: return stop("effect_context_mismatch")
    if not _review(requirement.get("review")): return stop("requirement_not_supported_by_researcher_review")
    if not _review(requirement.get("consumer_purpose_review")): return stop("consumer_purpose_review_missing")
    kind = requirement.get("kind")
    if kind not in KINDS: return stop("unsupported_requirement_kind")
    if kind == "post_update_consistency": return stop("field_core_state_and_relation_evaluation_not_established")
    for key in ("target_symbol", "mask_role"):
        if not _text(requirement.get(key)) or effect.get(key) != requirement[key]: return stop("symbolic_role_mismatch:" + key)
    if not _review(effect.get("role_review")): return stop("symbolic_role_review_missing")
    if effect.get("status") != "conditional_postcondition" or effect.get("path_status") != "structural_terminal":
        return stop("unknown_or_incomplete_effect_path")
    if effect.get("postcondition_complete") is not True: return stop("postcondition_completeness_not_established")
    post = effect.get("postcondition")
    if not isinstance(post, list) or not all(_text(symbol) for symbol in post) or len(post) != len(set(post)):
        return stop("postcondition_not_a_finite_unique_symbol_set")
    premises = effect.get("assumed_premises")
    if not isinstance(premises, list) or not all(_text(premise) for premise in premises) or not set(REQUIRED_PREMISES) <= set(premises):
        return stop("required_effect_premises_not_explicit")
    if not _guards(effect.get("condition_guards")): return stop("condition_guards_missing_or_malformed")
    result["condition_guards"] = deepcopy(effect["condition_guards"])
    result["unproved_premises"] = list(dict.fromkeys(result["unproved_premises"] + premises))
    result["symbolic_postcondition"] = list(post)
    if kind == "target_membership":
        present = requirement["target_symbol"] in post
        result.update(status="conditional_compatible" if present else "conditional_conflict", target_membership=present)
        return stop("symbolic_membership_only_under_explicit_premises")
    summary = requirement.get("search_summary")
    if (not isinstance(summary, dict) or not _review(summary.get("review"))
            or summary.get("weight") != "set_cardinality" or summary.get("iteration") != "complete_postcondition"
            or summary.get("singleton") != "bypass_search"):
        return stop("reviewed_search_cardinality_iteration_and_bypass_summary_missing")
    if summary.get("continuation_goal") != "obtain_witness_before_update" or not _review(summary.get("continuation_review")):
        return stop("reviewed_witness_before_update_continuation_goal_missing")
    if (summary.get("domain_condition") != "no_set_bits_outside_iteration_domain"
            or summary.get("stability_condition") != "mask_and_nr_cpu_ids_stable"):
        return stop("consumer_weight_iteration_domain_or_stability_condition_missing")
    result["unproved_premises"].append("reviewed_search_summary_applies_to_same_consumer_domain")
    result["unproved_premises"].append("reviewed_continuation_goal_applies_to_this_consumer_invocation")
    result["unproved_premises"].extend(["no_set_bits_outside_iteration_domain", "mask_and_nr_cpu_ids_stable"])
    if len(post) == 1:
        result.update(status="not_applicable", applicability_scope="search_route_only")
        return stop("singleton_bypasses_only_this_reviewed_search_route")
    if not post:
        result.update(status="conditional_conflict")
        return stop("empty_complete_domain_has_no_witness_for_reviewed_continuation_goal; existing_exit_is_not_actual_violation")
    return stop("nonempty_domain_does_not_establish_candidate_core_relation_or_witness")
