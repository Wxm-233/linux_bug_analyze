"""One frozen, bounded Python projection; no compiler, Git, or old extractor.

The root freezes code_identity.json before the single authorized invocation.
Expected values are used only by this wrapper after derivation/evaluation.
"""

import hashlib
import json
from pathlib import Path

from contract import UNKNOWN, derive_template, evaluate_model


BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parents[2]
PREVIOUS_RESULTS = WORKSPACE / "experiments/case_taxonomy/btrfs_first_consumer_20261011/results.json"
SETTER_SOURCE = WORKSPACE / "analysis_out/boundary-contracts-20260915-v2/btrfs/before/fs_btrfs_super.c"
COMMITS = {
    "before": "0d977e0eba234e01a60bdde27314dc21374201b3",
    "after": "6f93e834fa7c5faa0372e46828b4b2a966ac61d7",
}
HEADER_PATHS = {
    "fs/btrfs/ctree.h": "source/before_ctree.h",
    "include/asm-generic/unaligned.h": "source/before_include__asm-generic__unaligned.h",
}
SCOPE = "Known-case finite visible-source derivation and conditional Python byte/object projection; no C/kernel/mount execution."


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read_json(path):
    data = path.read_bytes()
    return json.loads(data.decode("utf-8-sig")), data


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _source_expectation_values(derived):
    """Observation only; no expected value is passed into derivation."""
    facts, template = derived["facts"], derived["template"]
    if template is None:
        return {"wire_type": None, "cached_type": None, "getter_macro": None,
                "reference_helper": None, "object_read_member": None,
                "actual_arch_header_binding": "unknown", "automatic_cfg_or_ready_claim": False}
    return {"wire_type": template["wire_type"], "cached_type": template["cached_type"],
            "getter_macro": facts["getter_macro"]["name"],
            "reference_helper": facts["reference_helper"]["name"],
            "object_read_member": facts["object_binding"]["read"]["member"],
            "actual_arch_header_binding": "unknown", "automatic_cfg_or_ready_claim": False}


def _comparison(actual, expected):
    _require(isinstance(expected, dict), "expected observation must be an object")
    checks = {key: actual.get(key) == value for key, value in expected.items()}
    return {"checks": checks, "passed": bool(checks) and all(checks.values()),
            "interpretation": "Post-hoc comparison against manually selected frozen development expectations; not blind accuracy or a defect label."}


def main():
    # Existing output makes another invocation fail before source derivation.
    _require(not (BASE / "results.json").exists(), "refusing to overwrite existing results.json")
    _require(not (BASE / "contract_template.json").exists(), "refusing to overwrite existing contract_template.json")
    identity, identity_bytes = _read_json(BASE / "code_identity.json")
    entries = identity.get("files")
    _require(isinstance(entries, list) and len(entries) == 2, "identity must freeze exactly two code files")
    _require(all(isinstance(item, dict) for item in entries), "invalid code identity entry")
    _require({item.get("path") for item in entries} == {"contract.py", "run.py"}, "identity code paths differ")
    for item in entries:
        _require(_sha((BASE / item["path"]).read_bytes()) == item.get("sha256"), "code identity mismatch: " + item["path"])
    protocol_bytes = (BASE / "protocol_pre.md").read_bytes()
    materials, materials_bytes = _read_json(BASE / "materials_pre.json")
    expectations, expectations_bytes = _read_json(BASE / "expectations_pre.json")
    previous, previous_bytes = _read_json(PREVIOUS_RESULTS)
    for key, data in (("protocol_sha256", protocol_bytes),
                      ("materials_sha256", materials_bytes),
                      ("expectations_sha256", expectations_bytes),
                      ("previous_results_sha256", previous_bytes)):
        _require(identity.get(key) == _sha(data), "frozen input identity mismatch: " + key)
    _require(materials.get("protocol_sha256") == _sha(protocol_bytes), "material protocol identity mismatch")
    material_entries = materials.get("materials")
    _require(isinstance(material_entries, list) and len(material_entries) == 4, "exactly four versioned header records required")
    expected_keys = {(version, path) for version in COMMITS for path in HEADER_PATHS}
    _require(all(isinstance(item, dict) for item in material_entries), "invalid material entry")
    _require({(item.get("version"), item.get("git_path")) for item in material_entries} == expected_keys, "header material version/path selection differs")
    source_bytes = {}
    for item in material_entries:
        version, git_path = item["version"], item["git_path"]
        _require(item.get("commit") == COMMITS[version], "material revision differs")
        _require(item.get("saved_path") == HEADER_PATHS[git_path], "material saved path differs")
        saved_path = item["saved_path"]
        if saved_path not in source_bytes:
            source_bytes[saved_path] = (BASE / saved_path).read_bytes()
        data = source_bytes[saved_path]
        _require(len(data) == item.get("bytes") and _sha(data) == item.get("sha256"), "header bytes/hash identity mismatch: " + saved_path)
    _require(len(source_bytes) == 2 and sum(map(len, source_bytes.values())) <= 768 * 1024, "bounded unique source byte limit exceeded")
    # These are the only C bytes read in this invocation.  Their hash is a
    # current reference identity, not re-authentication of previous acquisition.
    setter_bytes = SETTER_SOURCE.read_bytes()
    _require(identity.get("setter_source_sha256") == _sha(setter_bytes), "setter reference identity mismatch")
    setter = setter_bytes.decode("utf-8")
    header = source_bytes[HEADER_PATHS["fs/btrfs/ctree.h"]].decode("utf-8")
    generic = source_bytes[HEADER_PATHS["include/asm-generic/unaligned.h"]].decode("utf-8")
    pairs = previous.get("source_pairs")
    _require(isinstance(pairs, list) and len(pairs) == 2, "saved before/after source-pair records required")
    _require(all(isinstance(pair, dict) for pair in pairs), "invalid saved source-pair record")
    _require({pair.get("source_pair") for pair in pairs} == set(COMMITS), "saved source-pair versions differ")
    cases = expectations.get("cases")
    _require(isinstance(cases, list) and 0 < len(cases) <= 8, "case count must remain one through eight")
    _require(all(isinstance(case, dict) and isinstance(case.get("inputs"), dict) for case in cases), "invalid frozen model input")
    _require(len({case.get("id") for case in cases}) == len(cases), "case identifiers must be distinct")
    source_expectations = expectations.get("source_expectations")
    _require(isinstance(source_expectations, dict), "source expectations must be an object")
    derived_versions, observations, classification_counts = [], [], []
    for version in ("before", "after"):
        pair = next(pair for pair in pairs if pair["source_pair"] == version)
        records = pair.get("facts", {}).get("records")
        _require(isinstance(records, list) and len(records) == 1, "exactly one saved field candidate required per version")
        candidate = records[0]
        # Target field/getter/type originate here, never in source_expectations.
        derived = derive_template(header, generic, setter, candidate)
        derived_versions.append({"version": version, "commit": COMMITS[version],
                                 "saved_candidate_source": "previous results.json source_pairs facts.records[0]",
                                 "derivation": derived})
        observed_source = _source_expectation_values(derived)
        version_cases = []
        for case in cases:
            actual = evaluate_model(derived["template"], case["inputs"])
            # Expected and id are exposed only after evaluate_model returns.
            version_cases.append({"id": case.get("id"), "inputs": case["inputs"],
                                  "actual": actual, "expected": case.get("expected"),
                                  "validation": _comparison(actual, case.get("expected"))})
        observations.append({"version": version, "source_observations": observed_source,
                             "source_validation": _comparison(observed_source, source_expectations),
                             "cases": version_cases})
        counts = {status: sum(case["actual"]["status"] == status for case in version_cases)
                  for status in ("model_match", "model_mismatch", "not_consumed", "insufficient")}
        classification_counts.append({
            "version": version, "status_counts": counts,
            "entered_numeric_model": counts["model_match"] + counts["model_mismatch"],
            "cache_mismatch_count": sum(case["actual"]["cache_mismatch"] is True for case in version_cases),
            "behavior_difference_count": sum(case["actual"]["behavior_difference"] is True for case in version_cases),
            "cache_mismatch_without_behavior_difference_count": sum(
                case["actual"]["cache_mismatch"] is True and
                case["actual"]["behavior_difference"] is False for case in version_cases),
            "non_numeric_statuses_are_model_passes_or_defect_labels": False,
        })
    provenance = {
        "code_identity_sha256": _sha(identity_bytes), "code_identity": identity,
        "current_stage_input_identities_checked": True,
        "previous_results": {"path": PREVIOUS_RESULTS.relative_to(WORKSPACE).as_posix(),
                             "sha256": _sha(previous_bytes),
                             "previous_embedded_code_identity": previous.get("code_identity"),
                             "old_code_or_source_materials_reauthenticated": False,
                             "old_extractor_executed": False},
        "setter_reference": {"path": SETTER_SOURCE.relative_to(WORKSPACE).as_posix(),
                             "sha256": _sha(setter_bytes), "bytes": len(setter_bytes),
                             "interpretation": "Current frozen reference bytes checked; previous acquisition identity not re-authenticated."},
        "headers": material_entries,
        "unique_header_bytes_read": sum(map(len, source_bytes.values())),
        "unique_C_files_read": 1,
    }
    manual_selection = {
        "files": list(HEADER_PATHS) + ["fs/btrfs/super.c (existing before reference only)"],
        "functions": ["btrfs_sb", "btrfs_set_super"],
        "inherited_previous_stage_functions": previous.get("manual_function_selection"),
        "scope": "File/function/revision and eight-or-fewer model-input scope manually selected; target field/getter derived from saved candidate.",
    }
    template_document = {"scope": SCOPE, "provenance": provenance,
                         "manual_selection": manual_selection,
                         "source_pairs": derived_versions, "unknown": dict(UNKNOWN),
                         "automatic_CFG_or_readiness_claim": False,
                         "model_flags_are_source_execution_facts": False}
    all_passed = all(observation["source_validation"]["passed"] and
                     all(case["validation"]["passed"] for case in observation["cases"])
                     for observation in observations)
    results = {"scope": SCOPE, "provenance": provenance,
               "manual_selection": manual_selection, "source_pairs": derived_versions,
               "model_observations": observations, "bounded_case_count": len(cases),
               "version_model_evaluation_count": len(cases) * len(COMMITS),
               "same_frozen_cases_reused_across_versions": True,
               "classification_counts_by_version": classification_counts,
               "all_preregistered_checks_passed": all_passed,
               "preregistered_check_meaning": "Post-hoc observation comparisons matched expectations; this does not mean all cases entered or passed the numeric model.",
               "unknown": dict(UNKNOWN), "independent_positive_count": 0,
               "new_confirmed_defect_count": 0,
               "interpretation": "Cache equality and this-call clamp differences are separate conditional Python properties; non-consumption and insufficiency are not passes or defect labels. The saved before/after lexical source order is provenance, not an execution-path proof."}
    for filename, document in (("contract_template.json", template_document), ("results.json", results)):
        with (BASE / filename).open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({"scope": SCOPE, "versions": len(derived_versions),
                      "cases": len(cases), "model_evaluations": len(cases) * len(COMMITS),
                      "classification_counts_by_version": classification_counts,
                      "template_statuses": [item["derivation"]["status"] for item in derived_versions],
                      "all_preregistered_checks_passed": all_passed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
