"""Select bounded cross-architecture comparisons from reviewed metadata.

This is a pure finite-pool planner. Source semantics, legality, config-file
verification, adapter suitability and equivalence reviews are external inputs.
It does not infer those facts, inspect outcomes, or predict a violation.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from typing import Any


SCHEMA = "contrast_selection_v1"
PROFILE_FIELDS = {
    "id", "revision", "architecture", "purpose", "consumer", "execution",
    "configuration", "availability", "legality", "provider", "cost", "review",
}
CONTRACT_FIELDS = {
    "schema", "id", "purpose", "consumer", "execution", "required_config",
    "contrast_features", "review",
}
CONSUMER_FIELDS = {"interface", "operation", "stage", "object_role"}
FORBIDDEN_FEATURES = {"warn", "warning", "expected_violation", "outcome", "result",
                      "failure", "failure_label", "old", "fixed", "repair_status",
                      "architecture", "arch", "source_path", "path", "provider_signature",
                      "signature", "revision", "version", "old_fixed", "commit"}
# A bounded convenience normalization, not a proof of ISA identity. Unknown
# architecture identifiers still require the caller's external equivalence review.
ARCHITECTURE_ALIASES = {"s390x": "s390", "amd64": "x86_64", "x64": "x86_64",
                        "x86-64": "x86_64", "aarch64": "arm64"}


def metadata_sha256(value: Any) -> str:
    """Stable typed JSON identity for metadata and external review bindings."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def profile_binding(profile: dict[str, Any]) -> str:
    """Bind the review to identity, cost and all factual/semantic inputs."""
    return metadata_sha256({k: profile[k] for k in sorted(PROFILE_FIELDS - {"review"})})


def contract_binding(contract: dict[str, Any]) -> str:
    return metadata_sha256({k: contract[k] for k in sorted(CONTRACT_FIELDS - {"review"})})


def _text(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 512 and bool(value.strip())


def _architecture(value: str) -> str:
    normalized = value.strip().lower()
    return ARCHITECTURE_ALIASES.get(normalized, normalized)


def _digest(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _references(value: Any) -> bool:
    return (isinstance(value, list) and 0 < len(value) <= 32
            and all(_text(ref) for ref in value))


def _review(value: Any, binding: str) -> bool:
    return (isinstance(value, dict)
            and set(value) == {"status", "origin", "binding_sha256", "references"}
            and value["status"] == "reviewed" and value["origin"] == "researcher_review"
            and value["binding_sha256"] == binding and _references(value["references"]))


def _consumer(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == CONSUMER_FIELDS and all(_text(v) for v in value.values())


def _mapping(value: Any, *, maximum: int = 64) -> bool:
    return (isinstance(value, dict) and 0 < len(value) <= maximum
            and all(_text(k) and _text(v) for k, v in value.items()))


def _execution(value: Any) -> bool:
    return (isinstance(value, dict) and 0 < len(value) <= 16
            and all(_text(k) and (type(v) in {int, bool} or _text(v)) for k, v in value.items()))


def _contract_error(contract: Any) -> str | None:
    if not isinstance(contract, dict) or set(contract) != CONTRACT_FIELDS:
        return "contract_schema_mismatch"
    if (contract["schema"] != SCHEMA or not _text(contract["id"]) or not _text(contract["purpose"])
            or not _consumer(contract["consumer"]) or not _execution(contract["execution"])
            or not _mapping(contract["required_config"])):
        return "invalid_contract_scope"
    features = contract["contrast_features"]
    if (not isinstance(features, list) or not 0 < len(features) <= 16
            or not all(_text(x) for x in features) or len(set(features)) != len(features)
            or any(x.lower() in FORBIDDEN_FEATURES for x in features)):
        return "invalid_contrast_features"
    if not _review(contract["review"], contract_binding(contract)):
        return "contract_review_missing_or_mismatched"
    return None


def _profile_reasons(profile: Any, contract: dict[str, Any]) -> list[str]:
    if not isinstance(profile, dict) or set(profile) != PROFILE_FIELDS:
        return ["profile_schema_mismatch"]
    reasons = []
    if not all(_text(profile[k]) for k in ("id", "revision", "architecture", "purpose")):
        reasons.append("invalid_identity")
    if not _consumer(profile["consumer"]) or not _execution(profile["execution"]):
        reasons.append("invalid_consumer_or_execution")
    if profile["purpose"] != contract["purpose"]:
        reasons.append("different_purpose")
    if metadata_sha256(profile["consumer"]) != metadata_sha256(contract["consumer"]):
        reasons.append("different_consumer_or_stage")
    if metadata_sha256(profile["execution"]) != metadata_sha256(contract["execution"]):
        reasons.append("different_execution_context")
    if type(profile["cost"]) is not int or not 0 < profile["cost"] <= 1_000_000:
        reasons.append("invalid_cost")
    if profile["legality"] != "legal":
        reasons.append("legality_not_established")
    cfg = profile["configuration"]
    if (not isinstance(cfg, dict)
            or set(cfg) != {"sha256", "autoconf_sha256", "values", "facts_sha256", "verification"}
            or not _digest(cfg.get("sha256")) or not _digest(cfg.get("autoconf_sha256"))
            or not _mapping(cfg.get("values"), maximum=128)
            or cfg.get("facts_sha256") != metadata_sha256(cfg.get("values"))
            or cfg.get("verification") != "config_and_autoconf_verified"):
        reasons.append("actual_configuration_not_verified")
    elif any(cfg["values"].get(key) != expected for key, expected in contract["required_config"].items()):
        reasons.append("required_configuration_not_satisfied")
    available = profile["availability"]
    if (not isinstance(available, dict)
            or set(available) != {"build_status", "build_record_sha256", "image_sha256", "adapter", "adapter_stage", "references"}
            or available.get("build_status") != "archived_built"
            or not _digest(available.get("build_record_sha256")) or not _digest(available.get("image_sha256"))
            or not _text(available.get("adapter"))
            or available.get("adapter_stage") != contract["consumer"]["stage"]
            or not _references(available.get("references"))):
        reasons.append("build_or_adapter_not_established")
    provider = profile["provider"]
    if (not isinstance(provider, dict) or set(provider) != {"signature", "features", "references"}
            or not _text(provider.get("signature")) or not _mapping(provider.get("features"), maximum=16)
            or not _references(provider.get("references"))
            or any(f.lower() in FORBIDDEN_FEATURES for f in provider.get("features", {}))
            or any(feature not in provider.get("features", {}) for feature in contract["contrast_features"])):
        reasons.append("provider_semantics_incomplete")
    if not _review(profile["review"], profile_binding(profile)):
        reasons.append("profile_review_missing_or_mismatched")
    return reasons


def select_contrasts(contract: dict[str, Any], profiles: list[dict[str, Any]], *,
                     max_pairs: int, max_cost: int, seed: str) -> dict[str, Any]:
    """Return pairs and exclusions; a selected pair has NO predicted truth label.

    Budgets count both members afresh for each pair. This deliberately simple
    greedy policy is not an optimal scheduler or a claim of detection gain.
    Unknown legality/configuration/semantics is excluded and never deemed normal.
    Evidence digests and review bindings detect accidental drift; they do not
    independently authenticate the caller's factual or normative assertions.
    A small denylist rejects explicit identity/outcome feature names. Renaming
    such data cannot be detected mechanically; feature semantics require review.
    """
    result: dict[str, Any] = {"status": "invalid_input", "pairs": [], "profiles": [],
                              "pair_decisions": [], "spent_cost": 0,
                              "runtime_truth": "not_evaluated", "external_reviews_required": True}
    if (type(max_pairs) is not int or not 0 < max_pairs <= 8192
            or type(max_cost) is not int or not 0 < max_cost <= 1_000_000_000 or not _text(seed)):
        result["error"] = "invalid_budget_or_seed"
        return result
    try:
        error = _contract_error(contract)
        if error:
            result["error"] = error
            return result
        if not isinstance(profiles, list) or not 1 <= len(profiles) <= 128:
            result["error"] = "invalid_pool_size"
            return result
        ids = [p.get("id") if isinstance(p, dict) else None for p in profiles]
        if not all(_text(x) for x in ids) or len(set(ids)) != len(ids):
            result["error"] = "missing_or_duplicate_profile_id"
            return result
        by_id = {p["id"]: p for p in profiles}
        excluded = {}
        for name in sorted(by_id):
            reasons = _profile_reasons(by_id[name], contract)
            excluded[name] = reasons
            result["profiles"].append({"id": name, "status": "excluded" if reasons else "eligible", "reasons": reasons})
        candidates = []
        for left, right in itertools.combinations(sorted(by_id), 2):
            a, b = by_id[left], by_id[right]
            reasons = ["profile_ineligible:" + name for name in (left, right) if excluded[name]]
            decision: dict[str, Any] = {"left": left, "right": right, "reasons": reasons, "status": "excluded"}
            result["pair_decisions"].append(decision)
            if reasons:
                continue
            if a["revision"] != b["revision"]:
                reasons.append("different_revision")
            if _architecture(a["architecture"]) == _architecture(b["architecture"]):
                reasons.append("same_architecture")
            features = contract["contrast_features"]
            bits = [int(a["provider"]["features"][f] != b["provider"]["features"][f]) for f in features]
            if not any(bits):
                reasons.append("no_reviewed_semantic_contrast")
            if reasons:
                continue
            decision.update(different_features=[f for f, bit in zip(features, bits) if bit],
                            priority_bits=bits, cost=a["cost"] + b["cost"])
            tie = hashlib.sha256((seed + ":" + left + ":" + right).encode()).hexdigest()
            candidates.append((tuple(-bit for bit in bits), decision["cost"], tie, decision))
        for _, _, _, decision in sorted(candidates, key=lambda item: item[:3]):
            if len(result["pairs"]) >= max_pairs:
                decision["reasons"].append("pair_count_budget")
            elif result["spent_cost"] + decision["cost"] > max_cost:
                decision["reasons"].append("cost_budget")
            else:
                decision["status"] = "selected"
                result["pairs"].append({k: decision[k] for k in ("left", "right", "different_features", "priority_bits", "cost")})
                result["spent_cost"] += decision["cost"]
        result["status"] = "selected" if result["pairs"] else "insufficient"
        return result
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        result.update(status="invalid_input", pairs=[], spent_cost=0, error="malformed_metadata")
        return result
