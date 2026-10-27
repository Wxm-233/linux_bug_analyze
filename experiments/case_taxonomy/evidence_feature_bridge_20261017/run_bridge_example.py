"""Connect only pre-registered N1 JSON inputs; never open runtime outcomes."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "experiments/case_taxonomy"
sys.path.insert(0, str(ROOT))

from linux_bug_analyze.contrast_selection import select_contrasts
from linux_bug_analyze.evidence_feature_bridge import SCHEMA, project_provider_features, rules_binding


def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    protocol = json.loads((HERE / "protocol_pre.json").read_text(encoding="utf-8"))
    # This exact byte dictionary is the complete input read surface. No outcome,
    # source-tree, README, model-final or run-result glob/discovery is performed.
    artifacts = {}
    for rel in protocol["input_allowlist"]:
        path = (BASE / rel).resolve()
        assert path.is_relative_to(BASE.resolve())
        artifacts[rel] = path.read_bytes()
    digests = {path: hashlib.sha256(payload).hexdigest() for path, payload in artifacts.items()}
    payloads = {path: json.loads(payload.decode("utf-8-sig")) for path, payload in artifacts.items()}
    entry_path = "preparation_eligibility_20261016/entry_source_facts.json"
    guard_path = "preparation_eligibility_20261016/forward_paths.json"
    source_path = "preparation_eligibility_20261016/source_material.json"
    pool_path = "contrast_selection_20261017/example_pool.json"
    pool = payloads[pool_path]
    # Additional root-authorized identity-only reads. These bytes are not bridge
    # evidence and do not supply a desired result or a feature value.
    receipt_path = BASE / "contrast_selection_20261017/selection_receipt.json"
    original_selection_path = BASE / "contrast_selection_20261017/selection.json"
    prior_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    original_selection_sha = hashlib.sha256(original_selection_path.read_bytes()).hexdigest()
    assert digests[pool_path] == prior_receipt["pool_sha256"]
    assert original_selection_sha == prior_receipt["selection_sha256"]
    assert len(pool["profiles"]) <= protocol["real_pool"]["maximum_profiles"]

    def selector(artifact, pointer=""):
        return {"artifact": artifact, "sha256": digests[artifact], "pointer": pointer}

    def source_selector(fact):
        matches = [i for i, doc in enumerate(payloads[source_path]["documents"]) if doc["id"] == fact["document"]]
        assert len(matches) == 1
        return selector(source_path, "/documents/" + str(matches[0]))

    projections = []
    candidates = []
    for profile in pool["profiles"]:
        architecture = profile["architecture"]
        # Architecture maps to reviewed function roles/locations, never to an
        # instance answer. Values are computed from whatever matching facts exist.
        arch_directory = {"x86_64": "x86", "s390": "s390"}.get(architecture)
        assert arch_directory is not None
        entry_function = "smp_callin" if arch_directory == "x86" else "smp_start_secondary"
        preparation_call = "set_cpu_sibling_map" if arch_directory == "x86" else "update_cpu_masks"
        selectors = {}
        entries = [(key, fact) for key, fact in payloads[entry_path].items()
                   if fact["revision"] == profile["revision"] and fact["function"] == entry_function
                   and fact["path"].startswith("arch/" + arch_directory + "/")]
        if len(entries) == 1:
            key, fact = entries[0]
            selectors["entry"] = selector(entry_path, "/" + key)
            selectors["entry_source"] = source_selector(fact)
        guards = [(key, fact) for key, fact in payloads[guard_path].items()
                  if fact["revision"] == profile["revision"] and fact["function"] == "cpu_thread_map"
                  and fact["path"].startswith("arch/" + arch_directory + "/")]
        if len(guards) == 1:
            key, fact = guards[0]
            selectors["guard"] = selector(guard_path, "/" + key)
            selectors["guard_source"] = source_selector(fact)
        configured = [path for path, value in payloads.items()
                      if path.startswith("provider_consumer_binding_20261017/") and value["revision"] == profile["revision"]
                      and value["arch"] == arch_directory]
        if len(configured) == 1:
            selectors["configured"] = selector(configured[0])
        rules = {"schema": SCHEMA, "selectors": selectors,
                 "roles": {"preparation_call": preparation_call, "notification_call": "notify_cpu_starting",
                           "guard_parameter": "cpu", "guard_effect_call": "cpumask_set_cpu", "guard_effect_argument": 0},
                 "guard_domains": [{"predicate": "cpu_online", "trailing_arguments": [], "domain": "online_membership"},
                                   {"predicate": "cpumask_test_cpu", "trailing_arguments": ["&cpu_setup_mask"], "domain": "setup_membership"}]}
        rules["review"] = {"status": "reviewed", "origin": "researcher_review", "binding_sha256": rules_binding(rules),
                           "references": ["evidence_feature_bridge_20261017/protocol_pre.json",
                                          "assistant-reviewed function roles and guard normalization; not human-expert/effect approval"]}
        projected = project_provider_features(profile, artifacts, rules)
        projections.append({"profile_id": profile["id"], "rules": rules, "projection": projected})
        candidates.append(projected["profile_candidate"])
    bridged_pool = {"contract": pool["contract"], "profiles": candidates, "options": pool["options"]}
    # Contract feature requirements remain byte-equivalent as JSON data. There
    # is no phase fill-in, feature deletion or automatic approval before select.
    selection = select_contrasts(pool["contract"], candidates, **pool["options"])
    assert all((BASE / path).read_bytes() == artifacts[path] for path in artifacts)
    assert hashlib.sha256(original_selection_path.read_bytes()).hexdigest() == original_selection_sha
    save("bridge_pool.json", bridged_pool)
    save("bridge_selection.json", selection)
    save("bridge_results.json", {"schema": SCHEMA, "status": "bounded_bridge_complete_with_insufficiency",
         "profiles": projections, "input_hashes": digests,
         "formal_feature_count": sum(len(p["provider"]["features"]) for p in candidates),
         "original_pool_sha256": digests[pool_path], "original_inputs_unchanged": True,
         "input_hash_scope": "Runtime identity fingerprints; allowlist was preregistered, these seven digests were not frozen before execution",
         "prior_selection_receipt_check": {"pool_matches_receipt": True, "selection_matches_receipt": True,
                                            "selection_unchanged": True, "selection_sha256": original_selection_sha},
         "original_contract_unchanged": bridged_pool["contract"] == pool["contract"],
         "external_model_requests": 0, "new_builds": 0, "new_kernel_runs": 0,
         "scope": "Known development evidence; source CFG is trusted only within frozen extractor scope, not independently reparsed or effect-proved"})
    print(json.dumps({"status": selection["status"], "selected_pairs": len(selection["pairs"]),
        "profiles": [{"id": r["profile_id"], "call_order": r["projection"]["diagnostics"].get("call_order", {}).get("value"),
                      "eligibility_guard": r["projection"]["diagnostics"].get("eligibility_guard", {}).get("value"),
                      "configured_context": r["projection"]["diagnostics"].get("configured_context"),
                      "formal_features": r["projection"]["profile_candidate"]["provider"]["features"]} for r in projections]}))


if __name__ == "__main__":
    main()
