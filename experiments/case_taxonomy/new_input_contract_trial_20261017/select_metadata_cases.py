"""Freeze N2.6 metadata-only E/F selection from the previously registered 500.

This script does not inspect commit messages, source bodies, model labels, or outcomes.
The additional preselection contact exclusion is documented in contact_review.md.
"""

from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / "core_consumer_qualification_20261017"
OUT = HERE / "selection.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def choose_files(queue, changes):
    changed = {item["path"] for item in changes}
    implementation = [path for path in queue["implementation_paths"] if path in changed][:2]
    matched_header = [path for path in queue["header_paths"] if path in changed]
    header = (matched_header + [path for path in queue["header_paths"] if path not in matched_header])[:2]
    return {"public_implementation_paths": implementation, "public_header_paths": header,
            "planning_only": True, "existence_and_adequacy": "pending_exact_parent_collection"}


def main():
    if OUT.exists():
        raise SystemExit("Preserve the first N2.6 selection.json; do not replace or refill")
    trial = load(HERE / "protocol_pre.json")
    prior = load(OLD / "protocol_pre.json")
    old_selection = load(OLD / "selection.json")
    metadata = load(OLD / "git_metadata.json")
    exposure = load(OLD / "exposure_index.json")
    assert trial["selection"]["seed"] == prior["seed"] == old_selection["seed"]
    assert trial["selection"]["additional_exclusions"] == [
        "ba831b7b1a517ba7f25d6fa9736a8092d07b0c74",
        "bfcc4397435dc0407099b9a805391abc05c2313b",
    ]
    assert metadata["protocol_sha256"] == digest(OLD / "protocol_pre.json") == old_selection["protocol_sha256"]
    assert exposure["fixed_pool"]["manifest_sha256"] == metadata["pool_sha256"] == prior["pool_sha256"]
    assert digest(OLD / "git_metadata.json") == old_selection["metadata_sha256"]
    assert digest(OLD / "exposure_index.json") == old_selection["exposure_index_sha256"]
    assert len(metadata["records"]) == old_selection["pool_count"] == 500

    prior_exclusions = {commit: [reason] for commit, reason in prior["explicit_prior_exclusions"].items()}
    for group in ["known_source_read_or_method_development_exclude",
                  "documented_prior_13_case_family_exclude",
                  "confirmed_same_fix_family_only_exclude",
                  "possible_related_theme_defer_no_family_proof"]:
        for commit in exposure["exposure_sets"][group]:
            prior_exclusions.setdefault(commit, []).append(group)
    assert len(prior_exclusions) == old_selection["exclusion_count"]
    additional = {commit: ["N1.4h_selected_parent_source_and_repair_review"]
                  for commit in trial["selection"]["additional_exclusions"]}
    additional["bb7a5e44fc6f3d5a252d95c48d057d5beccb8b35"] = [
        "preselection_audit_found_prior_target_patch_and_function_discussion",
        "experiments/case_taxonomy/temporal_rule_v2_review.md:11",
    ]
    assert not set(additional) & set(prior_exclusions)
    excluded = {**prior_exclusions, **additional}
    exposure_by_hash = {record["hash"]: record for record in exposure["items"]}
    assert len(exposure_by_hash) == 500

    queue_results = []
    candidates = []
    selected_hashes = set()
    for case, queue, original in zip(("E", "F"), prior["queues_in_order"], old_selection["queues"], strict=True):
        assert queue["name"] == original["name"] and queue["quota"] == 1
        raw_ranked = []
        for record in metadata["records"]:
            if record["status"] != "single_parent_metadata":
                continue
            changed = {change["path"] for change in record["changes"]}
            implementations = sorted(changed.intersection(queue["implementation_paths"]))
            headers = sorted(changed.intersection(queue["header_paths"]))
            if not implementations and not headers or record["hash"] in prior_exclusions:
                continue
            rank = hashlib.sha256((prior["seed"] + ":" + record["hash"]).encode("utf-8")).hexdigest()
            raw_ranked.append((0 if implementations else 1, rank, record["hash"], record,
                               implementations + headers))
        raw_ranked.sort(key=lambda item: item[:3])
        assert [item[2] for item in raw_ranked] == original["ordered_hashes"], "Prior ranking changed"
        remaining = [item for item in raw_ranked if item[2] not in additional]
        selected = next((item for item in remaining if item[2] not in selected_hashes), None)
        if selected is not None:
            selected_hashes.add(selected[2])
            priority, rank, commit, record, matched = selected
            contact = exposure_by_hash[commit]
            assert len(record["parents"]) == 1
            candidates.append({
                "case": case, "hash": commit, "parent": record["parents"][0],
                "queue": queue["name"], "priority": priority, "rank_sha256": rank,
                "matched_paths": matched, "all_changes": record["changes"],
                "author": record["author"], "author_date": record["author_date"],
                "committer_date": record["committer_date"],
                "registered_implementation_paths": queue["implementation_paths"],
                "registered_header_paths": queue["header_paths"],
                "initial_file_plan": choose_files(queue, record["changes"]),
                "prior_contact_status": contact["contact_status"],
                "prior_source_review_evidence_paths": contact["source_review_evidence_paths"],
                "prior_family_status": contact["family_status"],
                "new_target_source_exposure": "not_found_in_bounded_preselection_records",
                "global_unseen_proved": False, "all_500_prior_screening_contact": True,
                "mechanism_and_normal_truth": "unknown_pending_parent_source",
            })
        queue_results.append({
            "case": case, "name": queue["name"], "registered_quota": 1,
            "previous_order": original["ordered_hashes"],
            "additional_excluded_hits": [{"hash": h, "reasons": additional[h]} for h in original["ordered_hashes"] if h in additional],
            "remaining_order": [{"hash": item[2], "priority": item[0], "rank_sha256": item[1],
                                  "parent": item[3]["parents"][0], "matched_paths": item[4],
                                  "prior_contact_status": exposure_by_hash[item[2]]["contact_status"],
                                  "prior_family_status": exposure_by_hash[item[2]]["family_status"]}
                                 for item in remaining],
            "selected_hash": selected[2] if selected else None,
        })
    assert len(candidates) <= 2 and len({item["hash"] for item in candidates}) == len(candidates)
    result = {
        "task": "N2.6_metadata_selection", "date": "2026-10-17",
        "protocol_sha256": digest(HERE / "protocol_pre.json"),
        "prior_protocol_sha256": digest(OLD / "protocol_pre.json"),
        "prior_selection_sha256": digest(OLD / "selection.json"),
        "metadata_sha256": digest(OLD / "git_metadata.json"),
        "exposure_index_sha256": digest(OLD / "exposure_index.json"),
        "seed": prior["seed"], "pool_count": 500,
        "excluded_hashes": excluded, "queues": queue_results, "candidates": candidates,
        "selection_policy": "same_prior_queue_priority_seed_rank_with_three_documented_preselection_exclusions",
        "selection_not_truth": True, "new_source_body_reads": 0, "new_model_requests": 0,
        "no_replacement_or_quota_transfer": True,
    }
    with OUT.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"selected": [{"case": x["case"], "hash": x["hash"], "parent": x["parent"],
                                    "initial_file_plan": x["initial_file_plan"]} for x in candidates],
                      "remaining_count": [len(q["remaining_order"]) for q in queue_results]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
