"""Offline evidence gate for one explicitly researcher-registered contract.

This is neither a C solver nor an automatic synthesis of the model's prose.
Only archived parsed final proposals are used; raw thinking is not read.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_ROOT = HERE.parent
MODEL = CASE_ROOT / "arch_witness_claude_20261014/compact_final"
REPLAY = CASE_ROOT / "arch_witness_checks_20261014/first_use_replay.py"
REVISION = "88b604263f3d6eedae0b1c2c3bbd602d1e2e8775"
RUNTIME_REVISIONS = {"old": REVISION, "fixed": "a052096bdd6809eeab809202726634d1ac975aa1"}
ARCH_KEYS = {"x86": "CONFIG_X86_64", "s390": "CONFIG_S390"}
REQUIRED = ("CONFIG_SMP", "CONFIG_SCHED_SMT", "CONFIG_SCHED_CORE")
REGISTERED = {"operator": "set_contains", "container": "cpu_smt_mask",
              "member": "target_cpu", "object": "same_target_cpu", "phase": "lock_snapshot"}
SCOPE = {"boot": "initial", "cpus": 2, "target_cpu": 1, "s390_mode": "SINGLE", "real_smt_coverage": "not_established"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def documents(request):
    result = {}
    if not isinstance(request, dict) or not isinstance(request.get("documents"), list):
        raise ValueError("missing supplied documents")
    for doc in request["documents"]:
        if not isinstance(doc, dict) or not all(isinstance(doc.get(k), str) and doc[k]
                                               for k in ("id", "kind", "path", "text")):
            raise ValueError("invalid document identity")
        lo, hi = doc.get("start_line"), doc.get("end_line")
        if type(lo) is not int or type(hi) is not int or lo < 1 or hi < lo:
            raise ValueError("invalid supplied range")
        lines = {}
        for line in doc["text"].splitlines():
            match = re.fullmatch(r"\s*(\d+): ?(.*)", line)
            if not match or int(match[1]) in lines:
                raise ValueError("invalid original numbered text")
            lines[int(match[1])] = match[2]
        if list(lines) != list(range(lo, hi + 1)) or doc["id"] in result:
            raise ValueError("supplied document missing/duplicate lines or id")
        result[doc["id"]] = (doc, lines)
    return result


def extract(index, refs):
    if not isinstance(refs, list):
        raise ValueError("references must be a list")
    out = []
    for ref in refs:
        if not isinstance(ref, dict) or ref.get("document") not in index:
            raise ValueError("unknown evidence document")
        doc, lines = index[ref["document"]]
        lo, hi = ref.get("start_line"), ref.get("end_line")
        if type(lo) is not int or type(hi) is not int or hi < lo or any(i not in lines for i in range(lo, hi + 1)):
            raise ValueError("evidence outside supplied original range")
        out.append({"document": doc["id"], "path": doc["path"], "kind": doc["kind"],
                    "start_line": lo, "end_line": hi,
                    "source_text": "\n".join(lines[i] for i in range(lo, hi + 1))})
    return out


def architecture(row):
    match = re.match(r"^arch/([^/]+)/", row["path"])
    return match[1] if row["kind"] == "source" and match else None


def configuration(rows):
    """Bind one configuration source to an architecture by its actual arch key.

    Do not combine separate partial documents into a fictitious effective config.
    """
    states = {}
    for arch, key in ARCH_KEYS.items():
        candidates = []
        for row in rows:
            if row["kind"] != "configuration":
                continue
            values = dict(re.findall(r"^(CONFIG_\w+)=(.*)$", row["source_text"], re.M))
            values.update({k: "n" for k in re.findall(r"^# (CONFIG_\w+) is not set$", row["source_text"], re.M)})
            if values.get(key) == "y":
                needed = REQUIRED + (("CONFIG_SCHED_TOPOLOGY",) if arch == "s390" else ())
                status = "disabled" if any(values.get(k) == "n" for k in needed) else (
                    "enabled" if all(values.get(k) == "y" for k in needed) else "missing")
                candidates.append({"document": row["document"], "path": row["path"],
                                   "status": status, "values": values})
        states[arch] = {"status": candidates[0]["status"] if len(candidates) == 1 else
                        "missing" if not candidates else "ambiguous", "sources": candidates}
    return states


def summarize(rows):
    configs = configuration(rows)
    return {"provider_architectures": sorted({a for r in rows if (a := architecture(r)) in ARCH_KEYS}),
            "configuration": configs,
            "common_consumer": any(r["kind"] == "source" and r["path"] == "kernel/sched/core.c"
                                   and "cpu_smt_mask" in r["source_text"] for r in rows)}


def evaluate_model(request, proposal):
    """Scope gate only; preserve model claims without inferring a predicate."""
    result = {"original_scope": proposal.get("scope") if isinstance(proposal, dict) else None,
              "status": "insufficient", "classification": "insufficient", "findings": [],
              "validated_detector": False, "predicate_origin": "not_inferred_from_prose"}
    try:
        index = documents(request)
        available = extract(index, [{"document": key, "start_line": doc["start_line"],
                                     "end_line": doc["end_line"]} for key, (doc, _) in index.items()])
        material = summarize(available)
        result["material_available"] = material
        if not isinstance(proposal, dict) or not isinstance(proposal.get("findings"), list):
            raise ValueError("missing findings list")
        for finding in proposal["findings"]:
            if not isinstance(finding, dict):
                raise ValueError("finding must be an object")
            cited = extract(index, finding.get("evidence"))
            summary = summarize(cited)
            missing = []
            for arch in ARCH_KEYS:
                if arch not in summary["provider_architectures"]:
                    missing.append("candidate.provider." + arch)
                if material["configuration"][arch]["status"] != "enabled":
                    missing.append("material.configuration." + arch)
                if summary["configuration"][arch]["status"] != "enabled":
                    missing.append("candidate.configuration." + arch)
            if not summary["common_consumer"]:
                missing.append("candidate.common_consumer")
            cross = len(summary["provider_architectures"]) == 2 and summary["common_consumer"] \
                and all(material["configuration"][a]["status"] == "enabled" for a in ARCH_KEYS)
            disabled = any(material["configuration"][a]["status"] == "disabled" for a in ARCH_KEYS)
            classification = "cross_arch_source_candidate" if cross else (
                "local_candidate" if summary["common_consumer"] else "insufficient")
            result["findings"].append({"classification": classification,
                "status": "not_applicable" if disabled else "candidate_only",
                "candidate_cited": summary, "extracted_evidence": cited, "missing": missing,
                "conditional_configuration_not_cited": cross and any(
                    summary["configuration"][a]["status"] != "enabled" for a in ARCH_KEYS),
                "structured_predicate_supplied": isinstance(finding.get("predicate"), dict),
                "validated_detector": False, "semantic_review_required": True})
        if result["findings"]:
            result["classification"] = "cross_arch_source_candidate" if any(
                x["classification"] == "cross_arch_source_candidate" for x in result["findings"]) else (
                "local_candidate" if any(x["classification"] == "local_candidate" for x in result["findings"]) else "insufficient")
            result["status"] = "not_applicable" if all(x["status"] == "not_applicable" for x in result["findings"]) else "candidate_only"
    except (KeyError, TypeError, ValueError) as exc:
        result.update(status="insufficient", classification="insufficient", error=str(exc), findings=[])
    return result


def evaluate_contract_card(card, request):
    result = {"status": "insufficient", "eligible_for_archived_replay": False,
              "origin": card.get("origin") if isinstance(card, dict) else None,
              "validated_detector": False, "missing": []}
    try:
        index = documents(request)
        if not isinstance(card, dict):
            raise ValueError("card must be an object")
        if card.get("schema_version") != 1 or card.get("id") != "researcher.bridge.self.v1" \
                or card.get("origin") != "researcher_synthesis":
            raise ValueError("unsupported contract id/schema/origin")
        if not isinstance(card.get("provenance"), dict) or card["provenance"].get("automatic_model_derivation") is not False:
            raise ValueError("researcher predicate provenance must explicitly deny automatic model derivation")
        if not isinstance(card.get("authority"), dict) or card["authority"].get("kind") != "consumer_necessary_condition":
            raise ValueError("unsupported or missing authority kind")
        if card.get("request_id") != request.get("id") or card.get("revision") != request.get("revision") \
                or request.get("revision") != REVISION:
            raise ValueError("card/request old-source binding mismatch")
        if card.get("scope") != SCOPE:
            raise ValueError("outside registered ordinary two-CPU initial SINGLE/non-SMT scope")
        predicate_present = "predicate" in card
        if predicate_present and card["predicate"] != REGISTERED:
            raise ValueError("unsupported predicate/object/phase; prose is not a predicate")
        if card.get("runtime_revision_scope") != RUNTIME_REVISIONS:
            raise ValueError("missing or unsupported archived runtime revision binding")
        evidence = card.get("evidence", {})
        layers = {}
        for layer in ("providers", "configuration"):
            block = evidence.get(layer)
            if not isinstance(block, dict) or set(block) != set(ARCH_KEYS):
                raise ValueError("missing " + layer + " architecture evidence")
            layers[layer] = {}
            for arch in ARCH_KEYS:
                rows = extract(index, block[arch])
                if not rows:
                    raise ValueError("missing " + layer + "." + arch)
                layers[layer][arch] = rows
        for layer in ("common_consumer", "predicate"):
            layers[layer] = extract(index, evidence.get(layer))
            if not layers[layer]:
                raise ValueError("missing " + layer)
        for arch in ARCH_KEYS:
            if any(architecture(row) != arch for row in layers["providers"][arch]):
                raise ValueError("provider path is not bound to " + arch)
            text = "\n".join(row["source_text"] for row in layers["providers"][arch])
            required = ("topology_sibling_cpumask", "set_cpu_sibling_map", "notify_cpu_starting", "smp_processor_id", "cpu_sibling_setup_mask") if arch == "x86" else (
                "topology_sibling_cpumask", "notify_cpu_starting(cpu)", "update_cpu_masks", "cpu_online(cpu)", "cpumask_set_cpu(cpu, &mask)", "thread_mask", "raw_smp_processor_id")
            if not all(token in text for token in required):
                raise ValueError("incomplete registered provider source anchors: " + arch)
            cfg = configuration(layers["configuration"][arch])[arch]
            if cfg["status"] == "disabled":
                result.update(status="not_applicable", missing=["explicitly disabled configuration: " + arch])
                return result
            if cfg["status"] != "enabled":
                raise ValueError("missing/ambiguous effective configuration: " + arch)
        common = layers["common_consumer"]
        texts = "\n".join(row["source_text"] for row in common)
        if any(row["kind"] != "source" or not row["path"].startswith(("kernel/", "include/linux/")) for row in common) \
                or not all(token in texts for token in ("cpu_smt_mask", "CPUHP_AP_SCHED_STARTING", "sched_cpu_starting", "sched_core_cpu_starting")):
            raise ValueError("missing common interface/callback chain")
        pred = layers["predicate"]
        text = "\n".join(row["source_text"] for row in pred if row["path"] == "kernel/sched/core.c")
        if not all(token in text for token in ("cpu_smt_mask(cpu)", "sched_core_lock(cpu, &flags)",
                                              "cpumask_weight(smt_mask) == 1", "for_each_cpu(t, smt_mask)", "raw_spin_lock_nested")):
            raise ValueError("missing registered first-consumer/predicate source anchors")
        if not predicate_present:
            result.update(status="candidate_only", evidence_layers=layers,
                          missing=["structured_predicate_not_supplied"], semantic_review_required=True)
            return result
        result.update(status="eligible_for_archived_replay", eligible_for_archived_replay=True,
                      evidence_layers=layers, predicate=card["predicate"], scope=card["scope"],
                      semantic_review_required=True,
                      limitation="Registered known-case researcher bridge, not automatically inferred or a validated general detector")
    except (KeyError, TypeError, ValueError) as exc:
        result["missing"].append(str(exc))
    return result


def load_replay():
    spec = importlib.util.spec_from_file_location("registered_archived_first_use", REPLAY)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def interpret_registered_predicate(predicate, mask, target_cpu):
    """Interpret only this registered bitset membership, never arbitrary code/text."""
    if predicate != REGISTERED:
        raise ValueError("unsupported predicate")
    if type(mask) is not int or not 0 <= mask < 16 or type(target_cpu) is not int or not 0 <= target_cpu < 4:
        raise ValueError("mask/CPU outside registered NR_CPUS=4 representation")
    return bool(mask & (1 << target_cpu))


def replay_archived():
    """Call only metadata/replay; never the dependency's output-writing main."""
    module = load_replay()
    materials, failures = [], []
    for profile in module.PROFILES:
        try:
            material = module.metadata(profile)
            material["checks"]["registered_runtime_revision"] = material["build"].get("revision") == RUNTIME_REVISIONS.get(material["build"].get("variant"))
            materials.append(material)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failures.append({"profile": profile, "status": "insufficient", "predicates": None, "error": str(exc)})
    pairs = {}
    for arch in ARCH_KEYS:
        pair = {m["build"]["variant"]: m for m in materials if m["details"]["arch"] == arch}
        diffs = {}
        if set(pair) == {"old", "fixed"}:
            old, fixed = pair["old"], pair["fixed"]
            diffs = {k: [old["cfg"].get(k), fixed["cfg"].get(k)] for k in set(old["cfg"]) | set(fixed["cfg"])
                     if old["cfg"].get(k) != fixed["cfg"].get(k)}
        valid = set(pair) == {"old", "fixed"} and set(diffs) <= {"CONFIG_LOCALVERSION"}
        for m in pair.values():
            m["checks"]["paired_config_only_localversion_differs"] = valid
        pairs[arch] = {"valid": valid, "differences": diffs}
    common = {path: len(materials) == 4 and len({m["source_hashes"].get(path) for m in materials}) == 1
                   and all(m["source_hashes"].get(path) is not None for m in materials)
              for path in ("kernel/cpu.c", "kernel/sched/core.c", "arch/x86/kernel/smpboot.c")}
    for m in materials:
        m["checks"]["shared_original_sources_agree"] = all(common.values())
    results = [module.replay(m) for m in materials] + failures
    for result in results:
        first = result.get("first_consumption", {})
        matches = first.get("cpu") == SCOPE["target_cpu"] == first.get("current") \
            and first.get("phase") == REGISTERED["phase"]
        if "foundation" in result:
            result["foundation"]["registered_target_cpu_and_phase"] = matches
        if not matches:
            result["status"], result["predicates"] = "insufficient", None
            result.setdefault("failed_foundation", []).append("registered_target_cpu_and_phase")
        result["registered_predicate_recomputed"] = None
        if matches and result["status"] in ("satisfied", "violation"):
            observed = interpret_registered_predicate(REGISTERED, first["mask"], SCOPE["target_cpu"])
            prior = result["predicates"]["first_use_contains_target"]["satisfied"]
            agrees = int(observed) == first.get("self") and observed is prior \
                and result["status"] == ("satisfied" if observed else "violation")
            result["foundation"]["registered_predicate_matches_archived_replay_and_self"] = agrees
            if agrees:
                result["registered_predicate_recomputed"] = observed
            else:
                result["status"], result["predicates"] = "insufficient", None
                result.setdefault("failed_foundation", []).append("registered_predicate_matches_archived_replay_and_self")
    # The dependency itself marks every recorded input read; no old result JSON is used.
    unchanged = all(module.digest((CASE_ROOT / rel).read_bytes()) == digest for rel, digest in module.INPUTS.items())
    if not unchanged:
        for result in results:
            result["status"], result["predicates"] = "insufficient", None
            result["registered_predicate_recomputed"] = None
            result.setdefault("failed_foundation", []).append("inputs_changed_during_replay")
    return {"profiles": results, "paired_config": pairs, "common_original_source_hashes_agree": common,
            "input_fingerprints": dict(module.INPUTS), "input_files_unchanged": unchanged,
            "dependency_sha256": sha(REPLAY), "new_boots": 0, "new_builds": 0,
            "registered_binding": {"target_cpu": SCOPE["target_cpu"], "phase": REGISTERED["phase"],
                                   "runtime_revisions": RUNTIME_REVISIONS},
            "independent_cases": 0, "external_calls": 0,
            "logical_source_example": {"kind": "source_logic_only_not_new_runtime", "online": False,
                                       "old_online_guard_allows_self_insertion": False,
                                       "conclusion": "Moving the old update earlier does not by itself change its online eligibility guard"},
            "limits": "Known-case archived observer source/config/log and recorded build/boot binding only; no fresh ELF certification, SMT, hotplug or concurrency result"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card", type=Path, default=HERE / "contract_card.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    if not args.out.resolve().is_relative_to(HERE):
        parser.error("Output must remain in this new experiment directory")
    manifest_path = HERE / "input_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    for relative, expected in manifest["files"].items():
        path = (HERE / relative).resolve()
        if not path.is_relative_to(CASE_ROOT) or sha(path) != expected:
            raise ValueError("Used-input binding mismatch: " + relative)
    if args.card.resolve() != (HERE / "contract_card.json").resolve():
        parser.error("Only the manifest-bound contract_card.json is supported by this CLI")
    fingerprints = {str(args.card.resolve()): sha(args.card), str(Path(__file__).resolve()): sha(__file__)}
    fingerprints[str(manifest_path)] = sha(manifest_path)
    for relative, expected in manifest["files"].items():
        fingerprints[str((HERE / relative).resolve())] = expected
    models, requests = {}, {}
    for view in ("pair", "ablated"):
        identifier = "startup_target_" + view
        req_path, proposal_path = MODEL / "requests" / (identifier + ".json"), MODEL / "proposals" / (identifier + ".json")
        request = json.loads(req_path.read_text(encoding="utf-8-sig"))
        proposal = json.loads(proposal_path.read_text(encoding="utf-8-sig"))
        requests[identifier] = request
        models[identifier] = evaluate_model(request, proposal)
        fingerprints[str(req_path.resolve())], fingerprints[str(proposal_path.resolve())] = sha(req_path), sha(proposal_path)
    card = json.loads(args.card.read_text(encoding="utf-8-sig"))
    gate = evaluate_contract_card(card, requests["startup_target_pair"])
    result = {"date": "2026-10-15", "model_source_gates": models, "researcher_card_gate": gate,
              "archived_replay": replay_archived() if gate["eligible_for_archived_replay"] else None,
              "current_input_fingerprints": fingerprints,
              "used_input_manifest_verified": True,
              "model_original_outputs_modified": False, "predicate_generated_by_model": False,
              "external_model_calls": 0, "new_cases": 0, "validated_general_detector": False}
    changed = [path for path, expected in fingerprints.items() if not Path(path).is_file() or sha(path) != expected]
    result["current_used_inputs_unchanged_at_end"] = not changed
    if changed:
        result["used_input_manifest_verified"] = False
        result["changed_inputs"] = changed
        result["model_source_gates"] = {key: {"status": "insufficient", "classification": "insufficient",
                                                     "reason": "used_inputs_changed_during_gate"} for key in models}
        gate.update(status="insufficient", eligible_for_archived_replay=False, missing=["used_inputs_changed_during_gate"])
        for row in (result["archived_replay"] or {}).get("profiles", []):
            row.update(status="insufficient", predicates=None, registered_predicate_recomputed=None)
            row.setdefault("failed_foundation", []).append("used_inputs_changed_during_gate")
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"card_status": gate["status"], "model_classifications": {k: v["classification"] for k, v in result["model_source_gates"].items()},
                      "replay": [{"profile": r["profile"], "status": r["status"]} for r in (result["archived_replay"] or {}).get("profiles", [])]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
