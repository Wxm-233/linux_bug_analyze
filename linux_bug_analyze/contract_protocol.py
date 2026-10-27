"""Bounded evaluation of explicit architecture contracts and reviewed evidence.

This module neither infers C semantics nor establishes normative authority.
The review ledger must be supplied separately from model proposals. A successful
relation is local to an observation; it is never whole-path correctness.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


SCHEMA = "architecture_contract_v1"
CLAIM_ROLES = {
    "authority", "interface", "consumer_requirement", "provider_binding",
    "object_binding", "deadline_binding", "applicability",
}
FIELD_ORIGINS = {"model_proposal", "program_projection", "researcher_authored"}
TYPES = {"bool", "int", "string", "int_set"}
ARITIES = {
    "contains": (2, 2), "nonempty": (1, 1), "eq": (2, 2), "ne": (2, 2),
    "lt": (2, 2), "le": (2, 2), "gt": (2, 2), "ge": (2, 2),
    "and": (2, 8), "or": (2, 8), "not": (1, 1),
}


class ContractError(ValueError):
    """Unsupported or insufficient evidence; never silently interpreted as false."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value))


def _same(left: Any, right: Any) -> bool:
    """Structural equality that does not treat bool as int (Python does)."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _value_type(value: Any) -> str:
    if type(value) is bool:
        return "bool"
    if type(value) is int and value.bit_length() <= 4096:
        return "int"
    if isinstance(value, str) and len(value) <= 256:
        return "string"
    if (isinstance(value, list) and len(value) <= 4096
            and all(type(x) is int and x.bit_length() <= 4096 for x in value)
            and len(set(value)) == len(value)):
        return "int_set"
    raise ContractError("unsupported, duplicate, nonfinite or oversized value")


def _infer(node: Any, symbols: Mapping[str, Any], used: set[str],
           budget: list[int], depth: int = 0) -> str:
    budget[0] += 1
    _require(depth <= 8 and budget[0] <= 64 and isinstance(node, dict), "invalid expression size/type")
    if set(node) == {"symbol"}:
        name = node["symbol"]
        _require(_identifier(name) and name in symbols, "unknown expression symbol")
        used.add(name)
        return symbols[name]["type"]
    if set(node) == {"literal"}:
        return _value_type(node["literal"])
    _require(set(node) == {"op", "args"}, "unsupported expression fields")
    op, args = node["op"], node["args"]
    _require(isinstance(op, str) and op in ARITIES and isinstance(args, list), "unsupported operator")
    lo, hi = ARITIES[op]
    _require(lo <= len(args) <= hi, "invalid operator arity")
    types = [_infer(arg, symbols, used, budget, depth + 1) for arg in args]
    if op == "contains":
        _require(types == ["int_set", "int"], "contains requires int_set/int")
    elif op == "nonempty":
        _require(types == ["int_set"], "nonempty requires int_set")
    elif op in {"eq", "ne"}:
        _require(types[0] == types[1], "equality requires identical types")
    elif op in {"lt", "le", "gt", "ge"}:
        _require(types == ["int", "int"], "ordering requires integers")
    else:
        _require(all(t == "bool" for t in types), "boolean operator requires bool")
    return "bool"


def validate_contract(contract: Mapping[str, Any]) -> dict[str, set[str]]:
    """Validate a finite expression envelope, not the truth of its proposed rule."""
    _require(isinstance(contract, dict) and contract.get("schema") == SCHEMA, "unsupported contract schema")
    _require(_identifier(contract.get("id")), "missing contract id")
    _require(isinstance(contract.get("revision"), str) and bool(contract["revision"]), "missing revision")
    _require(contract.get("authority_kind") in {"documented", "consumer_inferred"}, "unsupported authority kind")
    _require(contract.get("sufficient_for_correctness") is False, "only non-sufficient relations are supported")
    claims = contract.get("required_claims")
    _require(isinstance(claims, dict) and set(claims) == CLAIM_ROLES, "required claim roles are incomplete")
    _require(all(_identifier(value) for value in claims.values()), "invalid claim identifier")
    origins = contract.get("field_origins")
    fields = {"scope", "relation", "symbols", "required_claims", "authority_kind"}
    _require(isinstance(origins, dict) and set(origins) == fields
             and all(v in FIELD_ORIGINS for v in origins.values()), "field provenance is incomplete")
    symbols = contract.get("symbols")
    _require(isinstance(symbols, dict) and 0 < len(symbols) <= 64, "invalid symbols")
    for name, binding in symbols.items():
        _require(_identifier(name) and isinstance(binding, dict)
                 and set(binding) == {"type", "role"}, "malformed symbol declaration")
        _require(binding["type"] in TYPES and binding["role"] in {"configuration", "observation"}, "unsupported symbol type/role")
    used: dict[str, set[str]] = {}
    for label in ("scope", "relation"):
        used[label] = set()
        _require(_infer(contract.get(label), symbols, used[label], [0]) == "bool", "expression must yield bool")
    _require(bool(used["scope"]) and all(symbols[s]["role"] == "configuration" for s in used["scope"]), "scope requires explicit configuration symbols")
    _require(any(symbols[s]["role"] == "observation" for s in used["relation"]), "relation requires an observed symbol")
    _require(set(symbols) == used["scope"] | used["relation"], "unused symbols obscure the declared scope")
    return used


def _claim(ledger: Mapping[str, Any], name: Any, role: str, revision: str,
           allow_synthetic: bool) -> Mapping[str, Any]:
    _require(_identifier(name), "missing evidence claim")
    claim = ledger.get("claims", {}).get(name)
    _require(isinstance(claim, dict) and claim.get("role") == role, "missing/wrong evidence role: " + name)
    _require(claim.get("context_id") == ledger.get("context_id"), "claim belongs to a different configuration/run: " + name)
    _require(claim.get("status") == "supported", "unresolved/conflicting claim: " + name)
    allowed = {"researcher_review"}
    if role == "fact":
        allowed.add("program_projection")
    if allow_synthetic and ledger.get("basis") == "synthetic":
        allowed.add("synthetic_assumption")
    _require(claim.get("origin") in allowed, "unreviewed model/program semantic claim: " + name)
    _require(isinstance(claim.get("statement"), str) and bool(claim["statement"].strip()), "empty claim statement: " + name)
    refs = claim.get("references")
    _require(isinstance(refs, list) and bool(refs), "missing claim references: " + name)
    for ref in refs:
        _require(isinstance(ref, dict), "malformed reference")
        doc_id = ref.get("document")
        _require(_identifier(doc_id), "invalid document id")
        doc = ledger.get("documents", {}).get(doc_id)
        _require(isinstance(doc, dict) and doc.get("context_revision") == revision, "reference revision mismatch")
        _require(isinstance(doc.get("path"), str) and bool(doc["path"]), "missing document path")
        bounds = [doc.get("start_line"), ref.get("start_line"), ref.get("end_line"), doc.get("end_line")]
        _require(all(type(x) is int for x in bounds)
                 and 1 <= bounds[0] <= bounds[1] <= bounds[2] <= bounds[3], "reference outside registered document")
    return claim


def _expression(node: Mapping[str, Any], values: Mapping[str, Any]) -> Any:
    if "symbol" in node:
        return values[node["symbol"]]
    if "literal" in node:
        return node["literal"]
    args = [_expression(n, values) for n in node["args"]]
    op = node["op"]
    if op == "contains": return args[1] in args[0]
    if op == "nonempty": return bool(args[0])
    if op in {"eq", "ne"}:
        equal = set(args[0]) == set(args[1]) if isinstance(args[0], list) else args[0] == args[1]
        return equal if op == "eq" else not equal
    if op == "lt": return args[0] < args[1]
    if op == "le": return args[0] <= args[1]
    if op == "gt": return args[0] > args[1]
    if op == "ge": return args[0] >= args[1]
    if op == "and": return all(args)
    if op == "or": return any(args)
    return not args[0]


def _facts(names: set[str], contract: Mapping[str, Any], ledger: Mapping[str, Any],
           record: Mapping[str, Any], allow_synthetic: bool) -> dict[str, Any]:
    values = {}
    for name in sorted(names):
        spec = contract["symbols"][name]
        fact = record.get("facts", {}).get(name)
        _require(isinstance(fact, dict) and "value" in fact, "missing fact: " + name)
        claim = _claim(ledger, fact.get("claim"), "fact", contract["revision"], allow_synthetic)
        _require(_value_type(fact["value"]) == spec["type"], "fact type mismatch: " + name)
        expected = {"symbol": name, "value": fact["value"], "role": spec["role"],
                    "context_id": record["context_id"]}
        if spec["role"] == "observation":
            _require(fact.get("object_id") == record["object_id"], "fact belongs to a different object: " + name)
            _require(fact.get("event_id") == record["sample_event"], "fact belongs to a different event: " + name)
            expected.update(object_id=fact["object_id"], event_id=fact["event_id"])
        _require(_same(claim.get("fact"), expected), "fact does not match its reviewed projection: " + name)
        values[name] = fact["value"]
    return values


def evaluate_contract(contract: Mapping[str, Any], ledger: Mapping[str, Any],
                      record: Mapping[str, Any], *, allow_synthetic: bool = False) -> dict[str, Any]:
    """Return four-state, observation-scoped decisions under explicit premises.

    A ledger is an external reviewed input, not part of a model's self-approval.
    Reference bounds do not certify semantics. No sample-to-deadline promotion
    is supported: a later event cannot borrow the value of an earlier sample.
    """
    result = {
        "contract_id": contract.get("id") if isinstance(contract, dict) else None,
        "record_id": record.get("id") if isinstance(record, dict) else None,
        "applicability": "insufficient", "relation_at_observation": "insufficient",
        "relation_at_deadline": "insufficient", "whole_path": "insufficient",
        "authority_kind": contract.get("authority_kind") if isinstance(contract, dict) else None,
        "evaluation_basis": record.get("basis") if isinstance(record, dict) else None,
        "field_origins": contract.get("field_origins") if isinstance(contract, dict) else None,
        "reasons": [],
    }
    try:
        used = validate_contract(contract)
        _require(isinstance(ledger, dict) and isinstance(record, dict), "malformed ledger/record")
        _require(ledger.get("revision") == record.get("revision") == contract["revision"], "contract/ledger/record revision mismatch")
        _require(ledger.get("contract_id") == contract["id"], "review belongs to a different contract")
        _require(_same(ledger.get("field_origins"), contract["field_origins"]), "field provenance differs from external review")
        _require(isinstance(ledger.get("claims"), dict) and isinstance(ledger.get("documents"), dict), "malformed evidence index")
        _require(isinstance(record.get("facts"), dict), "malformed fact index")
        _require(record.get("basis") in {"synthetic", "source_projection", "archived_runtime"}, "unknown observation basis")
        _require(ledger.get("basis") == record["basis"], "ledger/record evidence tier mismatch")
        _require(_identifier(record.get("context_id")) and ledger.get("context_id") == record["context_id"], "configuration/run context mismatch")
        _require(record["basis"] != "synthetic" or allow_synthetic, "synthetic inputs require explicit opt-in")
        claims = contract["required_claims"]
        scope_review = _claim(ledger, claims["applicability"], "applicability", contract["revision"], allow_synthetic)
        _require(_same(scope_review.get("expression"), contract["scope"])
                 and _same(scope_review.get("symbols"), contract["symbols"]), "scope/symbols differ from reviewed applicability")
        values = _facts(used["scope"], contract, ledger, record, allow_synthetic)
        if not _expression(contract["scope"], values):
            for field in ("applicability", "relation_at_observation", "relation_at_deadline"):
                result[field] = "not_applicable"
            result["reasons"].append("Explicit scope is false for this selected contract only; other paths are not certified.")
            return result
        for role in sorted(CLAIM_ROLES - {"applicability"}):
            _claim(ledger, claims[role], role, contract["revision"], allow_synthetic)
        _require(ledger["claims"][claims["authority"]].get("authority_kind") == contract["authority_kind"], "authority kind is not externally reviewed")
        _require(ledger["claims"][claims["authority"]].get("supports_requirement") == claims["consumer_requirement"], "authority is not bound to the selected requirement")
        requirement = ledger["claims"][claims["consumer_requirement"]]
        _require(_same(requirement.get("expression"), contract["relation"])
                 and _same(requirement.get("symbols"), contract["symbols"]), "relation/symbols differ from the reviewed requirement")
        for key in ("object_id", "sample_event", "deadline_event"):
            _require(_identifier(record.get(key)), "missing object/event identity: " + key)
        _require(record.get("sample_kind") in {"sample", "pointer_acquisition", "content_consumption"}, "unknown sampling event kind")
        binding = record.get("observation_binding")
        _require(isinstance(binding, dict) and binding.get("object_id") == record["object_id"]
                 and binding.get("event_id") == record["sample_event"]
                 and binding.get("deadline_id") == record["deadline_event"], "inconsistent observation binding")
        reviewed = _claim(ledger, binding.get("claim"), "observation_binding", contract["revision"], allow_synthetic)
        expected_binding = {key: binding[key] for key in ("object_id", "event_id", "deadline_id")}
        expected_binding.update(context_id=record["context_id"], event_kind=record["sample_kind"])
        _require(_same(reviewed.get("binding"), expected_binding), "observation identity/event was not reviewed")
        for role in ("consumer_requirement", "provider_binding", "object_binding", "deadline_binding"):
            _require(ledger["claims"][claims[role]].get("object_id") == record["object_id"], "semantic claim belongs to a different object: " + role)
        _require(ledger["claims"][claims["deadline_binding"]].get("event_id") == record["deadline_event"], "consumption deadline is not externally reviewed")
        _require(ledger["claims"][claims["deadline_binding"]].get("event_kind") == "content_consumption", "deadline is not reviewed content consumption")
        result["applicability"] = "conditional_applicable"
        values.update(_facts(used["relation"], contract, ledger, record, allow_synthetic))
        decision = "satisfied" if _expression(contract["relation"], values) else "violated"
        result["relation_at_observation"] = decision
        if record["sample_event"] == record["deadline_event"] and record["sample_kind"] == "content_consumption":
            result["relation_at_deadline"] = decision
        else:
            result["reasons"].append("A separate sample establishes no value at the actual consumption deadline.")
        result["reasons"].append("Only the declared relation under reviewed premises was evaluated; not automatic extraction, normative fault attribution or whole-path correctness.")
    except (ContractError, TypeError, KeyError) as exc:
        result["reasons"].append(str(exc))
    return result
