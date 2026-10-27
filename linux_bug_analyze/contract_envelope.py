"""Shared builder for contract/ledger/record envelopes evaluated by ``contract_protocol``.

It only assembles the reviewed structure; it adds no semantics and approves nothing.
Every relation, role statement, reference and fact still comes from the caller, and
``evaluate_contract`` remains the sole judge. ``envelope_spec`` extracts only the
caller-supplied parameters from an existing envelope so that regression can show
an existing envelope is reproducible from those parameters alone.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any, Mapping

from .contract_protocol import CLAIM_ROLES

ORIGIN_FIELDS = ("scope", "relation", "symbols", "required_claims", "authority_kind")
DEFAULT_OBJECT_ROLES = ("consumer_requirement", "provider_binding", "object_binding", "deadline_binding")
_CLAIM_BASE = ("role", "status", "origin", "context_id", "statement", "references")
_LEDGER_BASE = ("contract_id", "revision", "basis", "context_id", "field_origins", "documents", "claims")
_RECORD_BASE = ("id", "revision", "basis", "context_id", "object_id", "sample_event", "deadline_event",
                "sample_kind", "facts", "observation_binding")


def document(path: Path, root: Path, revision: str, **extra: Any) -> dict[str, Any]:
    """Whole-file document entry; ``extra`` keeps fields such as source_revision."""
    text = Path(path).read_text(encoding="utf-8")
    entry = {"context_revision": revision, "path": str(Path(path).relative_to(root)).replace("\\", "/"),
             "start_line": 1, "end_line": len(text.splitlines()),
             "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    entry.update(extra)
    return entry


def whole(documents: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    return [{"document": name, "start_line": 1, "end_line": documents[name]["end_line"]}]


def symbol_type(value: Any) -> str:
    """Type from a value; an empty event sequence cannot be told from an empty int_set, declare it explicitly."""
    if type(value) is bool:
        return "bool"
    if isinstance(value, list):
        return "event_seq" if value and isinstance(value[0], list) else "int_set"
    if type(value) is int:
        return "int"
    return "string"


def symbols_used(*expressions: Any) -> set[str]:
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "symbol" in node:
                found.add(node["symbol"])
            for arg in node.get("args", []):
                walk(arg)
    for expr in expressions:
        walk(expr)
    return found


def build_envelope(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble one envelope from an explicit parameter mapping (see ``envelope_spec``)."""
    s = copy.deepcopy(dict(spec))
    prefix = s.get("claim_prefix", "review.")
    ctx, rev, basis = s["context_id"], s["revision"], s["basis"]
    obj, sample, deadline = s["object_id"], s["sample_event"], s["deadline_event"]
    symbols = s["symbols"]
    qualification = s.get("observation_qualification")
    default_fields = ORIGIN_FIELDS + (("observation_qualification",) if qualification is not None else ())
    origins = s.get("field_origins") or {k: "researcher_authored" for k in default_fields}
    contract = {"schema": s.get("schema", "architecture_contract_v1"), "id": s["contract_id"], "revision": rev,
                "authority_kind": s["authority_kind"], "sufficient_for_correctness": False,
                "field_origins": origins, "symbols": symbols,
                "required_claims": {role: prefix + role for role in CLAIM_ROLES},
                "scope": s["scope"], "relation": s["relation"]}
    if qualification is not None:
        contract["observation_qualification"] = qualification
    obs_id = s.get("observation_claim_id", prefix + "observation")
    record = {"id": s.get("record_id", s["contract_id"] + ".record"), "revision": rev, "basis": basis,
              "context_id": ctx, "object_id": obj, "sample_event": sample, "deadline_event": deadline,
              "sample_kind": s.get("sample_kind", "sample"), "facts": {},
              "observation_binding": {"object_id": obj, "event_id": sample, "deadline_id": deadline, "claim": obs_id}}
    record["observation_binding"].update(s.get("observation_binding_extra", {}))
    record.update(s.get("record_extra", {}))
    ledger = {"contract_id": s["contract_id"], "revision": rev, "basis": basis, "context_id": ctx,
              "field_origins": copy.deepcopy(origins), "documents": s["documents"], "claims": {}}
    ledger.update(s.get("ledger_extra", {}))
    object_roles = s.get("object_roles", list(DEFAULT_OBJECT_ROLES))
    for role in CLAIM_ROLES:
        given = s["role_claims"][role]
        claim = {"role": role, "status": given.get("status", "supported"), "origin": given.get("origin", "researcher_review"),
                 "context_id": ctx, "statement": given["statement"], "references": given["references"]}
        if role == "authority":
            claim.update(authority_kind=s["authority_kind"], supports_requirement=prefix + "consumer_requirement")
        if role == "applicability":
            claim.update(expression=copy.deepcopy(s["scope"]), symbols=copy.deepcopy(symbols))
        if role == "consumer_requirement":
            claim.update(expression=copy.deepcopy(s["relation"]), symbols=copy.deepcopy(symbols))
        if role in object_roles:
            claim["object_id"] = obj
        if role == "deadline_binding":
            claim.update(event_id=deadline, event_kind=s.get("deadline_event_kind", "content_consumption"))
        claim.update(given.get("extra", {}))
        ledger["claims"][prefix + role] = claim
    observation = s["observation_claim"]
    ledger["claims"][obs_id] = {"role": "observation_binding", "status": observation.get("status", "supported"),
                                "origin": observation.get("origin", "researcher_review"), "context_id": ctx,
                                "statement": observation["statement"], "references": observation["references"],
                                "binding": {"object_id": obj, "event_id": sample, "deadline_id": deadline,
                                            "context_id": ctx, "event_kind": s.get("sample_kind", "sample")}}
    if qualification is not None:
        ledger["claims"][obs_id]["qualification"] = copy.deepcopy(qualification)
    ledger["claims"][obs_id].update(observation.get("extra", {}))
    for name in s.get("fact_order", sorted(s["facts"])):
        fact = s["facts"][name]
        role = symbols[name]["role"]
        declared = {"symbol": name, "value": fact["value"], "role": role, "context_id": ctx}
        entry = {"value": fact["value"], "claim": fact.get("claim_id", "fact." + name)}
        if role == "observation":
            declared.update(object_id=obj, event_id=sample)
            entry.update(object_id=obj, event_id=sample)
        record["facts"][name] = entry
        ledger["claims"][entry["claim"]] = {"role": "fact", "status": fact.get("status", "supported"),
                                            "origin": fact.get("origin", "program_projection"), "context_id": ctx,
                                            "statement": fact["statement"], "references": fact["references"],
                                            "fact": declared}
    return {"contract": contract, "ledger": ledger, "record": record}


def envelope_spec(item: Mapping[str, Any]) -> dict[str, Any]:
    """Extract only caller-supplied parameters from an existing envelope.

    Structural parts (claim skeletons, bindings, declared facts) are *not* copied;
    ``build_envelope`` must regenerate them. Raises KeyError/ValueError when the
    envelope uses structure the builder cannot express.
    """
    c, l, r = item["contract"], item["ledger"], item["record"]
    required = c["required_claims"]
    prefix = required.get("interface", "")[: -len("interface")] if required.get("interface", "").endswith("interface") else None
    if prefix is None or set(required) != set(CLAIM_ROLES) or any(required[r] != prefix + r for r in CLAIM_ROLES):
        raise ValueError("non-uniform required claim names")
    obs_id = r["observation_binding"]["claim"]
    object_roles = [role for role in CLAIM_ROLES if "object_id" in l["claims"][prefix + role]]
    derived = {"authority": {"authority_kind", "supports_requirement"}, "applicability": {"expression", "symbols"},
               "consumer_requirement": {"expression", "symbols"}, "deadline_binding": {"event_id", "event_kind"}}
    role_claims = {}
    for role in CLAIM_ROLES:
        claim = l["claims"][prefix + role]
        skip = set(_CLAIM_BASE) | derived.get(role, set()) | ({"object_id"} if role in object_roles else set())
        role_claims[role] = {"statement": claim["statement"], "references": claim["references"],
                             "origin": claim["origin"], "status": claim["status"], "extra": {k: v for k, v in claim.items() if k not in skip}}
    obs = l["claims"][obs_id]
    facts, fact_order = {}, list(r["facts"])
    for name, entry in r["facts"].items():
        claim = l["claims"][entry["claim"]]
        facts[name] = {"value": entry["value"], "claim_id": entry["claim"], "origin": claim["origin"], "status": claim["status"],
                       "statement": claim["statement"], "references": claim["references"]}
    return {
        "schema": c["schema"], "contract_id": c["id"], "record_id": r["id"], "revision": c["revision"], "basis": r["basis"],
        "context_id": r["context_id"], "object_id": r["object_id"], "sample_event": r["sample_event"],
        "deadline_event": r["deadline_event"], "sample_kind": r["sample_kind"],
        "authority_kind": c["authority_kind"], "field_origins": c["field_origins"], "symbols": c["symbols"],
        "scope": c["scope"], "relation": c["relation"], "claim_prefix": prefix, "observation_claim_id": obs_id,
        "object_roles": object_roles,
        "deadline_event_kind": l["claims"][prefix + "deadline_binding"].get("event_kind"),
        "documents": l["documents"], "role_claims": role_claims,
        "observation_claim": {"statement": obs["statement"], "references": obs["references"], "origin": obs["origin"],
                              "status": obs["status"],
                              "extra": {k: v for k, v in obs.items() if k not in set(_CLAIM_BASE) | {"binding", "qualification"}}},
        **({"observation_qualification": c["observation_qualification"]} if "observation_qualification" in c else {}),
        "facts": facts, "fact_order": fact_order,
        "ledger_extra": {k: v for k, v in l.items() if k not in _LEDGER_BASE},
        "record_extra": {k: v for k, v in r.items() if k not in _RECORD_BASE},
        "observation_binding_extra": {k: v for k, v in r["observation_binding"].items()
                                      if k not in ("object_id", "event_id", "deadline_id", "claim")},
    }
