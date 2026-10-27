"""Predeclared raw-file identity adapter; existing lexical support is unchanged."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Both imported modules guard their mains.
    return module


OLD_PATH = HERE.parent / "aligned_contract_candidates_20261017/run_candidate_checks.py"
LOCATOR_PATH = HERE.parent / "preparation_eligibility_20261016/collect_sources.py"
old = load("n25_unchanged_checks", OLD_PATH)
locator = load("n26_unchanged_locator", LOCATOR_PATH)
SCHEMA = old.SCHEMA
sha = old.sha
require = old.require


def bind_documents(packet, artifacts):
    require(isinstance(packet, dict) and packet.get("schema") == SCHEMA, "packet_schema_mismatch")
    parents = packet.get("case_parents")
    require(isinstance(parents, dict) and len(parents) == 1
            and all(isinstance(k, str) and re.fullmatch(r"[A-Za-z0-9_-]+", k)
                    and isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v) for k, v in parents.items()),
            "single_case_parent_identity_required")
    docs = packet.get("documents")
    require(isinstance(docs, list) and 0 < len(docs) <= 8 and all(isinstance(d, dict) for d in docs), "documents_malformed")
    ids = [d.get("id") for d in docs]
    require(all(isinstance(x, str) and x.strip() for x in ids) and len(set(ids)) == len(ids), "document_id_ambiguous")
    manifest = packet.get("input_manifest")
    require(isinstance(manifest, list) and all(isinstance(x, dict) and set(x) == {"path", "sha256"} for x in manifest), "input_manifest_malformed")
    expected = {x["path"]: x["sha256"] for x in manifest}
    require(len(expected) == len(manifest), "duplicate_input_artifact")
    bound = {}
    for doc in docs:
        row = {"id": doc["id"], "status": "insufficient", "document": doc, "reasons": []}
        bound[doc["id"]] = row
        try:
            required = {"case", "parent", "revision", "profile", "kind", "function", "path", "text", "file_sha256",
                        "text_sha256", "configuration_sha256", "image_sha256", "preprocessed_sha256", "source_binding"}
            require(required <= set(doc) and doc["kind"] == "raw_source_file" and doc["function"] is None, "raw_document_schema_mismatch")
            case = doc["case"]
            require(isinstance(case, str) and case in parents and doc["parent"] == doc["revision"] == parents[case], "case_parent_mismatch")
            require(doc["profile"] == case + "_parent", "material_group_mismatch")
            require(all(doc[k] is None for k in ["configuration_sha256", "image_sha256", "preprocessed_sha256"]), "raw_source_has_configured_identity")
            require(isinstance(doc["text"], str) and sha(doc["text"].encode("utf-8")) == doc["text_sha256"] == doc["file_sha256"], "raw_file_digest_mismatch")
            source = doc["source_binding"]
            require(isinstance(source, dict) and set(source) == {"artifact", "artifact_sha256", "json_pointer"}, "source_binding_schema_mismatch")
            raw = artifacts[source["artifact"]]
            require(isinstance(raw, bytes) and sha(raw) == source["artifact_sha256"] == expected.get(source["artifact"]), "artifact_digest_mismatch")
            match = re.fullmatch(r"/documents/(0|[1-9][0-9]*)/text", source["json_pointer"])
            require(match is not None, "source_pointer_invalid")
            origin = json.loads(raw.decode("utf-8"))
            sources = origin.get("documents")
            require(isinstance(sources, list) and int(match[1]) < len(sources), "source_pointer_missing")
            item = sources[int(match[1])]
            require(isinstance(item, dict) and item.get("status") == "collected", "source_not_collected")
            require(all(item.get(k) == doc[k] for k in ["case", "revision", "path", "text"])
                    and item.get("material_group") == doc["profile"] and item.get("sha256") == doc["file_sha256"], "source_row_identity_mismatch")
            require(sha(item["text"].encode("utf-8")) == item["sha256"], "source_row_digest_mismatch")
            row.update(status="source_bound", text_sha256=doc["text_sha256"], source_binding=source,
                       material_group=doc["profile"], parent=doc["parent"], source_layer="raw_source_only")
        except (old.EvidenceError, KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
            row["reasons"].append(str(exc))
    return bound


def check_lexical_order(claim, bound):
    result = {"id": claim.get("id") if isinstance(claim, dict) else None, "status": "insufficient", "reasons": [],
              "source_layer": "raw_source_only", "configuration_applicability_proved": False,
              "control_flow_proved": False, "preparation_effect_proved": False}
    try:
        require(isinstance(claim, dict) and set(claim) == {"id", "kind", "profile", "document", "function", "first", "second", "expected", "evidence"}, "local_check_schema_mismatch")
        require(claim["kind"] == "lexical_call_order" and claim["expected"] in {"before", "after"}, "unsupported_local_relation")
        require(claim["document"] in bound and bound[claim["document"]]["status"] == "source_bound", "document_unbound")
        doc = bound[claim["document"]]["document"]
        require(claim["profile"] == doc["profile"] and isinstance(claim["function"], str)
                and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", claim["function"]), "material_group_or_function_invalid")
        evidence = old.evidence_spans(claim["evidence"], bound, profile=claim["profile"])
        result["evidence"] = evidence
        first_line, last_line, fragment = locator.complete_function(doc["text"].encode("utf-8"), claim["function"])
        require("\\\n" not in fragment and "\\\r\n" not in fragment, "line_splice_unsupported")
        tokens, pairs, _ = old._lex(fragment)
        body = old._function_body(tokens, pairs, claim["function"])
        anchors = []
        for key in ("first", "second"):
            anchor = claim[key]
            require(isinstance(anchor, dict) and type(anchor.get("line")) is int
                    and first_line <= anchor["line"] <= last_line, "anchor_outside_unique_function")
            require(any(e["document"] == doc["id"] and e["start_line"] <= anchor["line"] <= e["end_line"] for e in evidence), "anchor_not_covered_by_evidence")
            local = dict(anchor, line=anchor["line"] - first_line + 1)
            point = old._anchor(fragment, tokens, pairs, body, local)
            if point is not None:
                point = {**point, "fragment_line": point["line"], "line": point["line"] + first_line - 1,
                         "whole_file_character_offset": len("".join(doc["text"].splitlines(keepends=True)[:first_line - 1])) + point["character_offset"]}
            anchors.append(point)
        if any(x is None for x in anchors):
            result["reasons"] = ["call_anchor_not_in_frozen_supported_context"]
            return result
        first, second = anchors
        actual = "before" if first["character_offset"] < second["character_offset"] else "after" if first["character_offset"] > second["character_offset"] else "same_position"
        result.update(status="verified_lexical_order" if actual == claim["expected"] else "not_established",
                      observed_lexical_relation=actual, document=doc["id"], material_group=doc["profile"], parent=doc["parent"],
                      path=doc["path"], file_sha256=doc["file_sha256"], function=claim["function"],
                      function_slice={"first_line": first_line, "last_line": last_line, "sha256": sha(fragment.encode("utf-8"))}, anchors=anchors)
        if actual != claim["expected"]:
            result["reasons"] = ["expected_lexical_relation_not_established"]
    except (old.EvidenceError, KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        result["reasons"].append(str(exc))
    return result


def check_output(output, bound):
    require(isinstance(output, dict) and set(output) == {"schema", "requirements", "architecture_paths", "local_checks", "recommended_checks", "limits"}
            and output["schema"] == SCHEMA, "model_output_schema_mismatch")
    require(all(isinstance(output[k], list) for k in ["requirements", "architecture_paths", "local_checks", "recommended_checks", "limits"]), "output_lists_missing")
    require(len(output["requirements"]) <= 3 and len(output["local_checks"]) <= 6 and len(output["architecture_paths"]) <= 6, "model_output_bounds_exceeded")
    groups = {row["document"]["profile"] for row in bound.values() if row["status"] == "source_bound"}
    rows = []
    for group in ["requirements", "architecture_paths", "recommended_checks"]:
        for index, candidate in enumerate(output[group]):
            row = {"group": group, "index": index, "status": "insufficient", "semantic_review_required": True,
                   "source_layer": "raw_source_only", "check_scope": "source_identity_and_citations_only"}
            try:
                require(isinstance(candidate, dict), "candidate_not_object")
                if group == "architecture_paths":
                    require(isinstance(candidate.get("profile"), str) and candidate["profile"] in groups, "unknown_material_group")
                row["evidence"] = old.evidence_spans(candidate.get("evidence"), bound,
                    profile=candidate.get("profile") if group == "architecture_paths" else None)
                row["status"] = "source_bound_candidate"
            except (old.EvidenceError, KeyError, TypeError, ValueError, IndexError) as exc:
                row["reasons"] = [str(exc)]
            rows.append(row)
    return {"schema": SCHEMA, "candidate_bindings": rows, "local_checks": [check_lexical_order(x, bound) for x in output["local_checks"]],
            "formal_features_updated": False, "semantic_or_effect_proof": False,
            "material_groups_are_architecture_or_configuration_proof": False}


def validate_material_identity(packet, selection, initial, supplement=None):
    """Check selected parent/path metadata; no source content or truth inference."""
    selected = {x["case"]: x for x in selection["candidates"]}
    initial_cases = {x["case"]: x for x in initial["cases"]}
    require(len(selected) == len(selection["candidates"]) and len(initial_cases) == len(initial["cases"])
            and set(selected) == set(initial_cases), "selected_or_initial_cases_ambiguous")
    parents = packet.get("case_parents")
    require(isinstance(parents, dict) and len(parents) == 1, "single_case_parent_identity_required")
    allowed = {}
    for case, item in initial_cases.items():
        require(case in selected and item["parent"] == selected[case]["parent"]
                and item["hash"] == selected[case]["hash"], "initial_plan_selection_mismatch")
        chosen = selected[case]["initial_file_plan"]
        expected_paths = chosen["public_implementation_paths"] + chosen["public_header_paths"]
        require(item["paths"] == expected_paths, "initial_plan_path_mismatch")
        allowed[case] = set(item["paths"])
    if supplement is not None:
        rows = supplement.get("cases")
        require(isinstance(rows, list) and len({x["case"] for x in rows}) == len(rows), "supplement_cases_ambiguous")
        for item in rows:
            case, paths = item["case"], item["paths"]
            require(case in selected and item["parent"] == selected[case]["parent"], "supplement_parent_mismatch")
            require(isinstance(paths, list) and all(isinstance(p, str) for p in paths)
                    and len(paths) <= 4 and len(set(paths)) == len(paths)
                    and len([p for p in paths if not p.endswith(".h")]) <= 2
                    and len([p for p in paths if p.endswith(".h")]) <= 2, "supplement_file_budget")
            allowed[case].update(paths)
            require(len(allowed[case]) <= 8, "case_file_budget")
    for case, parent in parents.items():
        require(case in selected and case in allowed and parent == selected[case]["parent"], "packet_selected_parent_mismatch")
    seen = set()
    for doc in packet["documents"]:
        case, path = doc["case"], doc["path"]
        require(isinstance(path, str) and path and not PurePosixPath(path).is_absolute()
                and ".." not in PurePosixPath(path).parts, "git_path_malformed")
        require(case in parents and doc["parent"] == doc["revision"] == parents[case]
                and path in allowed[case], "document_outside_selected_material_plan")
        require((case, path) not in seen, "duplicate_case_path")
        seen.add((case, path))
    return {"status": "selected_parent_and_paths_bound", "case_parents": parents,
            "material_plan_is_semantic_truth": False}


def verify_baseline():
    baseline = json.loads((HERE / "adapter_baseline.json").read_text(encoding="utf-8"))
    require(baseline.get("schema") == "n26_raw_identity_adapter_baseline_v1", "method_baseline_missing")
    for relative, expected in {**baseline["files"], **baseline["metadata_files"]}.items():
        path = (ROOT / relative).resolve()
        require(path.is_relative_to(ROOT) and sha(path.read_bytes()) == expected, "frozen_method_changed:" + relative)
    return baseline


def main():
    parser = argparse.ArgumentParser()
    for name in ["documents", "manifest", "final", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "output_exists_preserve_prior_record")
    baseline = verify_baseline()
    baseline_sha = sha((HERE / "adapter_baseline.json").read_bytes())
    raw_packet = args.documents.read_bytes()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    old.packet_identity(raw_packet, manifest)
    packet = json.loads(raw_packet.decode("utf-8"))
    require(manifest.get("adapter_baseline_sha256") == baseline_sha, "packet_adapter_baseline_mismatch")
    selection_path = HERE / "selection.json"
    initial_path = HERE / "initial_material_plan.json"
    selection_sha = sha(selection_path.read_bytes())
    require(manifest.get("selection_sha256") == selection_sha, "packet_selection_mismatch")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    initial = json.loads(initial_path.read_text(encoding="utf-8"))
    require(initial["selection_sha256"] == selection_sha, "initial_plan_selection_digest_mismatch")
    plans = manifest.get("material_plans")
    require(isinstance(plans, list) and 1 <= len(plans) <= 2, "material_plan_manifest_missing")
    known = {initial_path.relative_to(ROOT).as_posix(): initial_path,
             (HERE / "supplement_material_plan.json").relative_to(ROOT).as_posix(): HERE / "supplement_material_plan.json"}
    plan_shas, supplement, seen_plans, plan_objects = set(), None, set(), {}
    for item in plans:
        name = item["path"]
        require(name in known and name not in seen_plans, "unregistered_or_duplicate_material_plan")
        seen_plans.add(name)
        raw_plan = known[name].read_bytes()
        require(sha(raw_plan) == item["sha256"], "material_plan_digest_mismatch")
        plan_shas.add(item["sha256"])
        plan_objects[item["sha256"]] = json.loads(raw_plan.decode("utf-8"))
        if known[name].name == "supplement_material_plan.json":
            supplement = json.loads(raw_plan.decode("utf-8"))
            require(supplement.get("selection_sha256") == selection_sha, "supplement_selection_digest_mismatch")
    require(initial_path.relative_to(ROOT).as_posix() in seen_plans, "initial_material_plan_missing")
    material_identity = validate_material_identity(packet, selection, initial, supplement)
    artifacts = {}
    for item in packet["input_manifest"]:
        path = (ROOT / item["path"]).resolve()
        require(path.is_relative_to(ROOT), "artifact_outside_project")
        artifacts[item["path"]] = path.read_bytes()
        origin = json.loads(artifacts[item["path"]].decode("utf-8"))
        require(origin.get("adapter_baseline_sha256") == baseline_sha
                and origin.get("material_plan_sha256") in plan_shas, "source_collection_plan_identity_mismatch")
        collection_plan = {x["case"]: x for x in plan_objects[origin["material_plan_sha256"]]["cases"]}
        for row in origin["documents"]:
            require(row["case"] in collection_plan and row["revision"] == collection_plan[row["case"]]["parent"]
                    and row["path"] in collection_plan[row["case"]]["paths"], "source_row_outside_its_collection_plan")
    bound = bind_documents(packet, artifacts)
    receipt = json.loads((args.receipt or args.final.parent / "receipt.json").read_text(encoding="utf-8"))
    plan = json.loads((args.plan or args.final.parent / "call_plan.json").read_text(encoding="utf-8"))
    require(receipt.get("status") == "complete_final_received" and receipt.get("exit_code") == 0
            and receipt.get("result_subtype") == "success" and receipt.get("result_is_error") is not True, "delivery_not_complete")
    require(receipt.get("actual_models") == receipt.get("response_models") == ["AWS-Claude-Opus-5.5"], "delivery_model_mismatch")
    require(isinstance(receipt.get("stop_reasons"), list) and receipt["stop_reasons"]
            and set(receipt["stop_reasons"]) <= {"end_turn", "stop_sequence"}
            and receipt.get("refusal_observed") is False, "delivery_stop_or_refusal_gate_failed")
    require(plan.get("prompt_sha256") == manifest["prompt_sha256"], "delivery_prompt_mismatch")
    final = args.final.read_bytes()
    require(bool(final.strip()), "empty_final")
    result = {"documents_sha256": sha(raw_packet), "raw_final_sha256": sha(final), "source_layer": "raw_source_only",
              "selected_material_identity": material_identity,
              "document_bindings": [{k: v for k, v in row.items() if k != "document"} for row in bound.values()]}
    try:
        output, result["parse_mode"] = old.parse_final(final)
        result.update(check_output(output, bound))
        result["status"] = "bounded_raw_source_checks_complete"
    except (old.EvidenceError, ValueError, TypeError) as exc:
        result.update(status="insufficient", error=str(exc))
    require(args.final.read_bytes() == final, "final_changed_during_check")
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "documents_bound": sum(x["status"] == "source_bound" for x in bound.values()),
                      "local_statuses": [x["status"] for x in result.get("local_checks", [])]}))


if __name__ == "__main__":
    main()
