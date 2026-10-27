"""Project existing bounded source facts without manufacturing effective features.

The supported inputs describe local call order and guarded helper structure.
They are not preparation-effect certificates. This version therefore emits
diagnostics, clears manual feature answers and leaves the two effective feature
fields insufficient. External rule review supplies meaning, not instance values.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from .contrast_selection import metadata_sha256


SCHEMA = "evidence_feature_bridge_v1"
FIELDS = ("qualification_domain", "preparation_phase")


class EvidenceError(ValueError):
    pass


def rules_binding(rules: dict[str, Any]) -> str:
    return metadata_sha256({k: v for k, v in rules.items() if k != "review"})


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 1024


def _require(condition, reason):
    if not condition:
        raise EvidenceError(reason)


def _arch(value):
    _require(_text(value), "architecture_identity_missing")
    normalized = value.lower().strip()
    return {"x86_64": "x86", "amd64": "x86", "s390x": "s390", "aarch64": "arm64"}.get(normalized, normalized)


def _select(artifacts, selector):
    _require(isinstance(selector, dict) and set(selector) == {"artifact", "sha256", "pointer"}, "selector_missing_or_malformed")
    path, expected, pointer = (selector[k] for k in ("artifact", "sha256", "pointer"))
    _require(_text(path) and path in artifacts and isinstance(artifacts[path], bytes), "artifact_missing")
    payload = artifacts[path]
    actual = hashlib.sha256(payload).hexdigest()
    _require(actual == expected, "artifact_digest_mismatch")
    _require(isinstance(pointer, str) and (not pointer or pointer.startswith("/")) and pointer.count("/") <= 12,
             "json_pointer_invalid")
    value = json.loads(payload.decode("utf-8-sig"))
    if pointer:
        for part in pointer[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                _require(bool(re.fullmatch(r"0|[1-9][0-9]*", part)), "json_pointer_invalid")
                index = int(part)
                _require(index < len(value), "json_pointer_missing")
                value = value[index]
            else:
                _require(isinstance(value, dict) and part in value, "json_pointer_missing")
                value = value[part]
    return value, {"artifact": path, "artifact_sha256": actual, "json_pointer": pointer}


def _source_identity(fact, source, profile, provenance):
    _require(isinstance(fact, dict) and isinstance(source, dict), "source_identity_missing")
    for key, source_key in [("document", "id"), ("revision", "revision"), ("path", "path"),
                            ("function", "function"), ("source_sha256", "function_sha256")]:
        _require(_text(fact.get(key)) and fact[key] == source.get(source_key), "source_identity_mismatch:" + key)
    _require(fact["revision"] == profile.get("revision"), "profile_revision_mismatch")
    pieces = fact["path"].split("/")
    _require(len(pieces) > 2 and pieces[0] == "arch", "source_architecture_unbound")
    _require(_arch(pieces[1]) == _arch(profile.get("architecture")), "source_architecture_mismatch")
    _require(bool(re.fullmatch(r"[0-9a-f]{64}", fact["source_sha256"])), "source_digest_invalid")
    _require(isinstance(source.get("text"), str)
             and hashlib.sha256(source["text"].encode("utf-8")).hexdigest() == source.get("function_sha256"),
             "source_text_digest_mismatch")
    return {**provenance, "revision": fact["revision"], "source_path": fact["path"],
            "function": fact["function"], "source_sha256": fact["source_sha256"],
            "source_scope": "unpreprocessed bounded local source structure"}


def _call_order(fact, roles):
    _require(fact.get("status") == "bounded_local_flow", "entry_flow_not_bounded")
    paths = fact.get("paths")
    _require(isinstance(paths, list) and 0 < len(paths) <= 64, "entry_paths_missing")
    _require(isinstance(fact.get("calls"), list) and all(isinstance(x, dict) for x in fact["calls"]), "entry_direct_calls_missing")
    orders, locations = [], []
    for index, path in enumerate(paths):
        _require(isinstance(path, dict) and isinstance(path.get("exit"), dict) and path["exit"].get("kind") in {"return", "function_end"},
                 "entry_path_incomplete")
        events = path.get("events")
        _require(isinstance(events, list) and all(isinstance(x, dict) for x in events), "entry_path_events_missing")
        _require(all(type(e.get("line")) is int and type(e.get("column")) is int
                     and e["line"] > 0 and e["column"] > 0 for e in events), "entry_event_coordinates_invalid")
        coordinates = [(e["line"], e["column"]) for e in events]
        _require(all(a < b for a, b in zip(coordinates, coordinates[1:])), "entry_events_not_in_source_order")
        chosen = []
        for role in ("preparation_call", "notification_call"):
            matches = [(i, event) for i, event in enumerate(events) if event.get("callee") == roles[role]]
            _require(len(matches) == 1, "missing_or_multiple_role_calls:" + role)
            position, event = matches[0]
            direct = [c for c in fact["calls"] if c.get("callee") == event["callee"]
                      and c.get("line") == event.get("line") and c.get("column") == event.get("column")]
            _require(len(direct) == 1 and direct[0].get("direct") is True, "role_call_not_directly_bound")
            chosen.append((position, event))
        orders.append("preparation_call_before_notification" if chosen[0][0] < chosen[1][0]
                      else "preparation_call_after_notification")
        locations.append({"path_index": index, "guards": path.get("guards", []),
                          "preparation": {k: chosen[0][1][k] for k in ("line", "column")},
                          "notification": {k: chosen[1][1][k] for k in ("line", "column")}})
    _require(len(set(orders)) == 1, "conflicting_call_order_across_paths")
    return {"status": "supported_local_structure", "value": orders[0], "locations": locations,
            "assumptions": fact.get("assumptions", []), "effective_preparation_proved": False,
            "runtime_reachability_proved": False, "target_object_coverage_proved": False}


def _guard_candidate(fact, roles, guard_domains):
    _require(fact.get("status") in {"partial_forward_structure", "bounded_forward_structure"}, "guard_flow_not_supported")
    parameters = fact.get("parameters")
    target = roles["guard_parameter"]
    _require(isinstance(parameters, list), "guard_parameters_missing")
    matches = [(i, p) for i, p in enumerate(parameters) if isinstance(p, dict) and p.get("name") == target]
    _require(len(matches) == 1, "guard_target_parameter_ambiguous")
    parameter_index, parameter = matches[0]
    _require(isinstance(fact.get("shadowed_names"), list) and not fact["shadowed_names"], "guard_shadowing_not_supported")
    paths = fact.get("paths")
    _require(isinstance(paths, list) and 0 < len(paths) <= 64, "guard_paths_missing")
    domains, locations, frontier = [], [], False
    for index, path in enumerate(paths):
        _require(isinstance(path, dict) and isinstance(path.get("events"), list)
                 and all(isinstance(x, dict) for x in path["events"]), "guard_path_malformed")
        frontier |= path.get("status") != "structural_terminal"
        setters = [e for e in path["events"] if e.get("callee") == roles["guard_effect_call"]]
        _require(len(setters) <= 1, "multiple_effect_calls_in_path")
        for event in setters:
            arguments = event.get("arguments", [])
            _require(isinstance(arguments, list), "effect_arguments_malformed")
            _require(type(event.get("line")) is int and type(event.get("column")) is int
                     and event["line"] > 0 and event["column"] > 0, "effect_coordinates_invalid")
            arg_index = roles["guard_effect_argument"]
            _require(type(arg_index) is int and 0 <= arg_index < len(arguments), "effect_argument_missing")
            arg = arguments[arg_index]
            expected_declaration = {"parameter": parameter_index, "line": parameter.get("line"), "column": parameter.get("column")}
            _require(isinstance(arg, dict) and arg.get("text") == target
                     and arg.get("binding") == "source_local_value_version" and arg.get("version") == "parameter"
                     and arg.get("declaration") == expected_declaration, "effect_target_parameter_not_bound")
            found = []
            guards = event.get("guards_at_event", [])
            _require(isinstance(guards, list) and all(isinstance(g, dict) for g in guards), "guard_records_malformed")
            for guard in guards:
                _require(isinstance(guard.get("expression"), str) and type(guard.get("taken")) is bool, "guard_record_malformed")
                for rule in guard_domains:
                    arguments_text = ", ".join([target, *rule["trailing_arguments"]])
                    expression = "!" + rule["predicate"] + "(" + arguments_text + ")"
                    if (re.sub(r"\s+", "", guard.get("expression", "")) == re.sub(r"\s+", "", expression)
                            and guard.get("taken") is False):
                        _require(type(guard.get("line")) is int and type(event.get("line")) is int
                                 and guard["line"] < event["line"], "eligibility_guard_not_before_effect")
                        found.append((rule["domain"], guard))
            _require(len(found) == 1, "eligibility_guard_missing_or_ambiguous")
            domains.append(found[0][0])
            locations.append({"path_index": index, "guard": found[0][1],
                              "effect_call": {k: event[k] for k in ("line", "column")},
                              "parameter": expected_declaration})
    _require(bool(domains), "no_guarded_effect_call")
    _require(len(set(domains)) == 1, "conflicting_eligibility_domains")
    return {"status": "supported_guard_candidate", "value": domains[0], "locations": locations,
            "unsupported_frontier_present": frontier, "assumptions": fact.get("assumptions", []),
            "effective_preparation_proved": False, "runtime_reachability_proved": False}


def _configured_context(binding, profile, sources):
    _require(isinstance(binding, dict), "configured_binding_missing")
    _require(binding.get("revision") == profile.get("revision"), "configured_revision_mismatch")
    _require(_arch(binding.get("arch")) == _arch(profile.get("architecture")), "configured_architecture_mismatch")
    configuration = profile.get("configuration")
    _require(isinstance(configuration, dict), "profile_configuration_malformed")
    selected = binding.get("selected_artifacts")
    _require(isinstance(selected, list) and all(isinstance(x, dict) and isinstance(x.get("path"), str) for x in selected),
             "configured_artifact_records_malformed")
    configs = [x for x in selected if x["path"].endswith("/.config")]
    _require(len(configs) == 1 and configs[0].get("sha256") == configuration.get("sha256"),
             "configured_profile_digest_mismatch")
    originals = binding.get("original_sources")
    _require(isinstance(originals, list) and all(isinstance(x, dict) for x in originals), "configured_source_records_malformed")
    for source in sources:
        matching = [x for x in originals if x.get("path") == source.get("path")]
        _require(len(matching) == 1 and matching[0].get("revision") == profile.get("revision")
                 and matching[0].get("sha256") == source.get("full_file_sha256"), "configured_original_source_mismatch")
    # An .i region/ET_REL symbol link by itself is not this raw-source CFG.
    return {"status": "identity_bound_only", "configuration_sha256": configs[0]["sha256"],
            "active_configured_flow_proved": False, "helper_effects_proved": False}


def project_provider_features(profile: dict[str, Any], artifacts: dict[str, bytes], rules: dict[str, Any]) -> dict[str, Any]:
    """Replace manual answers with provenance-bearing projections or unknowns.

    Artifacts are exact JSON bytes supplied by the caller, not filenames opened
    here. Selectors bind an artifact digest and JSON pointer. Rules supply
    reviewed call roles and guard normalization, never per-profile feature values.
    This version has no effect-certificate schema; local diagnostics therefore
    never satisfy the original effective preparation features, even in a fully
    context-matched synthetic test. All changed profiles need a fresh review.
    """
    malformed_profile = not isinstance(profile, dict) or not isinstance(profile.get("provider"), dict)
    candidate = copy.deepcopy(profile) if isinstance(profile, dict) else {}
    if not isinstance(candidate.get("provider"), dict):
        candidate["provider"] = {"signature": "unknown"}
    candidate["provider"]["features"] = {}
    candidate["provider"]["references"] = []
    candidate["review"] = {"status": "unreviewed", "origin": "program_projection",
                           "binding_sha256": "", "references": []}
    result = {"status": "insufficient", "profile_candidate": candidate,
              "fields": {name: {"status": "insufficient", "value": None,
                                "reasons": ["local_structure_not_effect_completion", "no_supported_preparation_effect_certificate"],
                                "evidence": []} for name in FIELDS},
              "diagnostics": {}, "reasons": [], "semantic_review_proved_by_adapter": False}
    try:
        _require(not malformed_profile, "profile_schema_malformed")
        _require(isinstance(rules, dict) and set(rules) == {"schema", "selectors", "roles", "guard_domains", "review"}
                 and rules["schema"] == SCHEMA, "rules_schema_mismatch")
        review = rules["review"]
        _require(isinstance(review, dict) and review.get("status") == "reviewed"
                 and review.get("origin") == "researcher_review" and review.get("binding_sha256") == rules_binding(rules)
                 and isinstance(review.get("references"), list) and bool(review["references"]), "rules_review_missing_or_stale")
        roles = rules["roles"]
        _require(isinstance(roles, dict) and set(roles) == {"preparation_call", "notification_call", "guard_parameter",
                                                         "guard_effect_call", "guard_effect_argument"}
                 and all(_text(roles[k]) for k in roles if k != "guard_effect_argument")
                 and roles["preparation_call"] != roles["notification_call"], "roles_malformed")
        domains = rules["guard_domains"]
        _require(isinstance(domains, list) and 0 < len(domains) <= 16, "guard_rules_missing")
        _require(all(isinstance(x, dict) and set(x) == {"predicate", "trailing_arguments", "domain"}
                     and _text(x["predicate"]) and _text(x["domain"]) and isinstance(x["trailing_arguments"], list)
                     and all(_text(a) for a in x["trailing_arguments"]) for x in domains), "guard_rules_malformed")
        selectors = rules["selectors"]
        _require(isinstance(selectors, dict) and not set(selectors) - {"entry", "entry_source", "guard", "guard_source", "configured"},
                 "unsupported_selector_role")
        sources = []
        for kind, diagnostic, field in [("entry", "call_order", "preparation_phase"), ("guard", "eligibility_guard", "qualification_domain")]:
            evidence = []
            try:
                fact, fact_ref = _select(artifacts, selectors.get(kind))
                evidence.append(fact_ref)
                source, source_ref = _select(artifacts, selectors.get(kind + "_source"))
                evidence.append(source_ref)
                identity = _source_identity(fact, source, profile, fact_ref)
                evidence[0] = identity
                sources.append(source)
                projection = _call_order(fact, roles) if kind == "entry" else _guard_candidate(fact, roles, domains)
                projection["evidence"] = evidence
                projection["profile_configuration_binding"] = "not_established_by_raw_source_facts"
                result["diagnostics"][diagnostic] = projection
                result["fields"][field]["evidence"] = projection["evidence"]
            except (EvidenceError, KeyError, TypeError, ValueError, IndexError) as exc:
                reason = str(exc)
                result["diagnostics"][diagnostic] = {"status": "insufficient", "value": None, "reasons": [reason], "evidence": evidence}
                result["fields"][field]["evidence"] = evidence
                result["fields"][field]["reasons"].append(reason)
        context_evidence = []
        try:
            binding, context_ref = _select(artifacts, selectors.get("configured"))
            context_evidence.append(context_ref)
            context = _configured_context(binding, profile, sources)
            context["evidence"] = [context_ref]
            result["diagnostics"]["configured_context"] = context
            context_reason = "active_configured_flow_and_preparation_effects_unproved"
        except (EvidenceError, KeyError, TypeError, ValueError, IndexError) as exc:
            context_reason = str(exc)
            result["diagnostics"]["configured_context"] = {"status": "insufficient", "reasons": [context_reason], "evidence": context_evidence}
        for field in result["fields"].values():
            field["reasons"].append(context_reason)
            field["evidence"].extend(context_evidence)
        refs = []
        for diagnostic in result["diagnostics"].values():
            for evidence in diagnostic.get("evidence", []):
                refs.append(evidence["artifact"] + "#" + evidence["json_pointer"])
        candidate["provider"]["references"] = sorted(set(refs))
        result["reasons"] = ["original_effective_features_not_established", "profile_review_invalidated"]
    except (EvidenceError, KeyError, TypeError, ValueError, IndexError) as exc:
        result["reasons"].append(str(exc))
    return result
