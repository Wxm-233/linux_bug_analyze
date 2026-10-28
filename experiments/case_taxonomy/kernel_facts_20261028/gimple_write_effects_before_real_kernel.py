"""Source-bound observations of direct scalar writes in one early-CFG record.

This adapter reuses the existing CFG and statement parsers.  A matching spelling
on an assignment's left side is an observation, not a declaration/alias binding,
an external-state guarantee, execution evidence, or a must-write proof.
"""
from __future__ import annotations

import hashlib
import re

from .gimple_cfg_facts import BB, _view, analyze_cfg
from .gimple_local_flow import _classify, _units


SCOPE = "selected_function_scalar_spelling"
SYMBOL = re.compile(r"[A-Za-z_]\w*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _shadow_facts(text, function, target):
    """Report visible declarations without inventing a global symbol resolver."""
    mask, _, _, _ = _view(text)
    first = BB.search(mask)
    signature = re.search(r"\b" + re.escape(function) + r"\s*\((.*?)\)\s*\{", mask[:first.start()], re.S)
    facts = []
    if re.search(r"\b" + re.escape(target) + r"\b", signature[1]):
        facts.append({"kind": "parameter_spelling_present", "scope": "function_parameter",
                      "pointer_or_aggregate_possible": bool(re.search(r"\*|\b(?:struct|union)\b", signature[1]))})
    prefix = mask[signature.end():first.start()]
    for start, end, forced in _units(prefix, prefix, {}):
        event = _classify(" ".join(prefix[start:end].split()))
        if forced is None and target in event.get("declares", []):
            facts.append({"kind": "local_declaration", "scope": "function_local", "code": prefix[start:end].strip(),
                          "pointer_or_aggregate_possible": bool(re.search(r"\*|\b(?:struct|union)\b", prefix[start:end]))})
    return facts


def analyze_write_effects(document, *, function, target, expected_sha256=None):
    """Observe supported direct assignments, retaining CFG and unknown effects.

    ``document`` must contain exactly one complete compiler early-CFG function,
    including the metadata accepted by :func:`analyze_cfg`.  Callers must select
    that function before supplying a multi-function dump. ``target`` is an exact
    simple identifier; fields, dereferences, arrays and SSA-name normalization
    are deliberately unsupported. ``expected_sha256`` binds UTF-8 document text.
    """
    result = {"status": "insufficient", "scope": SCOPE, "function": function, "target": target,
              "source_sha256": None, "document": None, "path": None, "revision": None,
              "writes": [], "unknowns": [], "shadow_facts": [], "branch_polarity": [], "branch_arms": [],
              "unconditional_write_proved": False, "runtime_reachability_proved": False,
              "external_state_binding_proved": False, "target_scalar_type_proved": False,
              "no_global_or_indirect_effect_proved": False}
    if not isinstance(document, dict) or not isinstance(document.get("text"), str):
        result["unknowns"].append({"reason": "missing_document_text"})
        return result
    result.update({key: document.get(key) for key in ("document", "path", "revision")})
    result["document"] = document.get("id")
    text = document["text"]
    result["source_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if not isinstance(function, str) or not SYMBOL.fullmatch(function) or not isinstance(target, str) or not SYMBOL.fullmatch(target):
        result["unknowns"].append({"reason": "function_or_exact_scalar_identifier_unsupported"})
        return result
    if expected_sha256 is not None and (not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256)
                                         or expected_sha256 != result["source_sha256"]):
        result["unknowns"].append({"reason": "source_sha256_binding_mismatch"})
        return result
    cfg = analyze_cfg(document)
    if cfg["status"] != "compiler_normal_graph_facts":
        result["unknowns"] = cfg["unknowns"]
        return result
    if cfg["function"] != function:
        result["unknowns"].append({"reason": "selected_function_mismatch", "observed": cfg["function"]})
        return result
    result["shadow_facts"] = _shadow_facts(text, function, target)
    result["branch_polarity"] = cfg["branch_polarity"]
    result["branch_arms"] = cfg["branch_arms"]
    result["unknowns"] = list(cfg["unknowns"])
    unsupported_target_definition = False
    for block in cfg["blocks"]:
        for event in block["events"]:
            if target not in event.get("defines", []):
                continue
            if event["kind"] != "scalar_assign":
                unsupported_target_definition = True
                result["unknowns"].append({"reason": "target_definition_outside_supported_scalar_assignment",
                                           "event": event["id"], "kind": event["kind"]})
                continue
            context = [{"branch_event": arm["branch_event"], "condition": arm["condition"], "arm": name,
                        "linear_join": arm["linear_join"], "semantics": arm["semantics"]}
                       for arm in cfg["branch_arms"] for name, prefix in arm["prefixes"].items() if block["id"] in prefix]
            result["writes"].append({key: event[key] for key in (
                "id", "block", "kind", "code", "raw", "defines", "uses", "start_offset", "end_offset",
                "dump_line_start", "dump_line_end", "source_locations", "assignment_kind")})
            result["writes"][-1].update(source_sha256=result["source_sha256"], branch_context=context,
                                        branch_context_complete=False, execution_proved=False,
                                        external_state_binding_proved=False)
    pointer_target = any(item["pointer_or_aggregate_possible"] for item in result["shadow_facts"])
    if pointer_target:
        result["unknowns"].append({"reason": "target_has_visible_pointer_or_aggregate_declaration"})
    if result["writes"] and not pointer_target:
        result["status"] = "direct_write_observed"
    elif not pointer_target and not unsupported_target_definition and not any(
            item.get("kind") in {"opaque", "asm", "clobber"} for item in result["unknowns"]):
        result["status"] = "no_direct_write_observed"
    return result


def check_write_candidate(document, candidate):
    """Bind a candidate to the current text; never upgrade it to a must effect.

    Supported candidate keys: ``function``, ``target``, ``source_sha256``,
    ``claim`` (``direct_write_exists`` or ``unconditional_write``) and optional
    ``scope``.  External/global/indirect effects require a separate resolver.
    """
    result = {"status": "insufficient", "reason": "invalid_candidate", "facts": None,
              "scope": SCOPE, "unconditional_write_proved": False, "external_state_binding_proved": False}
    if not isinstance(candidate, dict):
        return result
    if not isinstance(candidate.get("source_sha256"), str) or not SHA256.fullmatch(candidate["source_sha256"]):
        result["reason"] = "candidate_source_binding_required"
        return result
    facts = analyze_write_effects(document, function=candidate.get("function"), target=candidate.get("target"),
                                  expected_sha256=candidate["source_sha256"])
    result["facts"] = facts
    if facts["status"] == "insufficient":
        result["reason"] = "insufficient_bound_facts"
    elif candidate.get("scope", SCOPE) != SCOPE or candidate.get("external_state") or candidate.get("global"):
        result["reason"] = "external_or_other_scope_not_proved"
    elif candidate.get("claim") == "unconditional_write":
        result["reason"] = "unconditional_or_must_write_not_proved"
    elif candidate.get("claim") != "direct_write_exists":
        result["reason"] = "unsupported_candidate_claim"
    elif facts["status"] == "direct_write_observed":
        result.update(status="observed", reason="direct_assignment_spelling_in_selected_function")
    else:
        # A missing supported direct write is not a proof of no state effects.
        result["reason"] = "no_supported_direct_write_observed_not_global_absence"
    return result
