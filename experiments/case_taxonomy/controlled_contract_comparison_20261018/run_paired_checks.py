"""Audit the same unchanged final with the frozen N2.5 implementation."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
SOURCE_PATH = "experiments/case_taxonomy/aligned_contract_candidates_20261017/documents.json"
CHECKER_PATH = "experiments/case_taxonomy/aligned_contract_candidates_20261017/run_candidate_checks.py"
WRAPPER_PATH = "experiments/case_taxonomy/controlled_contract_comparison_20261018/run_paired_checks.py"
LEXER_PATH = "linux_bug_analyze/preprocessed_evidence.py"
REQUIRED_METHOD_FILES = {WRAPPER_PATH, CHECKER_PATH, LEXER_PATH}

spec = importlib.util.spec_from_file_location("n28_frozen_n25_checks", ROOT / CHECKER_PATH)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)  # The old main is guarded; no trial runs on import.
require, sha = old.require, old.sha


def verify_method_baseline(baseline_path=HERE / "method_baseline.json", root=ROOT):
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    require(baseline.get("schema") == "n28_paired_method_baseline_v1", "method_baseline_schema_mismatch")
    files = baseline.get("files")
    require(isinstance(files, dict) and REQUIRED_METHOD_FILES <= set(files), "required_frozen_method_missing")
    for relative, expected in files.items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root.resolve()) and sha(path.read_bytes()) == expected,
                "frozen_method_changed:" + relative)
    return baseline


def load_packet(manifest, root=ROOT):
    require(manifest.get("documents_path") == SOURCE_PATH, "source_packet_path_mismatch")
    raw = (root / SOURCE_PATH).read_bytes()
    old.packet_identity(raw, manifest)
    packet = json.loads(raw.decode("utf-8-sig"))
    require(manifest.get("input_manifest") == packet.get("input_manifest")
            and isinstance(packet.get("input_manifest"), list), "source_input_manifest_mismatch")
    artifacts = {}
    for item in packet["input_manifest"]:
        path = (root / item["path"]).resolve()
        require(path.is_relative_to(root.resolve()), "artifact_outside_project")
        require(item["path"] not in artifacts, "duplicate_input_artifact")
        raw_artifact = path.read_bytes()
        require(sha(raw_artifact) == item["sha256"], "source_artifact_digest_mismatch:" + item["path"])
        artifacts[item["path"]] = raw_artifact
    return raw, packet, artifacts


def verify_delivery(receipt, plan, manifest):
    require(isinstance(receipt, dict) and isinstance(plan, dict), "delivery_record_malformed")
    require(receipt.get("status") == "complete_final_received" and receipt.get("exit_code") == 0
            and receipt.get("result_subtype") == "success" and receipt.get("result_is_error") is not True,
            "delivery_not_complete")
    require(receipt.get("actual_models") == receipt.get("response_models") == ["AWS-Claude-Opus-5.5"],
            "delivery_model_mismatch")
    stops = receipt.get("stop_reasons")
    require(isinstance(stops, list) and stops and all(isinstance(x, str) for x in stops)
            and set(stops) <= {"end_turn", "stop_sequence"} and receipt.get("refusal_observed") is False,
            "delivery_stop_or_refusal_gate_failed")
    require(isinstance(manifest.get("prompt_sha256"), str)
            and plan.get("prompt_sha256") == manifest["prompt_sha256"], "delivery_prompt_mismatch")


def bind_repeat_paths(repeat, manifest, final_path, receipt_path=None, plan_path=None, outer=ROOT.parent):
    require(repeat in {"X", "Y"}, "repeat_invalid")
    rows = manifest.get("repeats")
    require(isinstance(rows, list) and len(rows) == 2 and all(isinstance(x, dict) for x in rows)
            and {x.get("repeat") for x in rows} == {"X", "Y"}, "repeat_manifest_invalid")
    allowed_root = (outer / "模型调用测试").resolve()
    directories = {}
    for row in rows:
        name = row.get("directory")
        require(isinstance(name, str) and name and not Path(name).is_absolute()
                and ".." not in Path(name).parts, "repeat_directory_invalid")
        directory = (outer / name).resolve()
        require(directory.is_relative_to(allowed_root) and directory != allowed_root, "repeat_directory_outside_model_root")
        directories[row["repeat"]] = directory
    require(len(set(directories.values())) == 2, "repeat_directories_not_distinct")
    directory = directories[repeat]
    expected = [directory / "final.md", directory / "receipt.json", directory / "call_plan.json"]
    actual = [final_path, receipt_path or expected[1], plan_path or expected[2]]
    for label, path, target in zip(["final", "receipt", "plan"], actual, expected):
        require(path.resolve() == target.resolve(), "repeat_" + label + "_path_mismatch")
    return tuple(expected)


def run(repeat, final_path, output_path, receipt_path=None, plan_path=None):
    require(not output_path.exists(), "output_exists_preserve_prior_record")
    verify_method_baseline()
    manifest = json.loads((HERE / "packet_manifest.json").read_text(encoding="utf-8"))
    final_path, receipt_path, plan_path = bind_repeat_paths(repeat, manifest, final_path, receipt_path, plan_path)
    raw_documents, packet, artifacts = load_packet(manifest)
    bound = old.bind_documents(packet, artifacts)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    verify_delivery(receipt, plan, manifest)
    raw_final = final_path.read_bytes()
    require(bool(raw_final.strip()), "empty_final")
    result = {
        "repeat": repeat, "source_task_directory": final_path.parent.relative_to(ROOT.parent.resolve()).as_posix(),
        "source_final": final_path.relative_to(ROOT.parent.resolve()).as_posix(),
        "documents_sha256": sha(raw_documents), "raw_final_sha256": sha(raw_final),
        "method_baseline_sha256": sha((HERE / "method_baseline.json").read_bytes()),
        "packet_manifest_sha256": sha((HERE / "packet_manifest.json").read_bytes()),
        "document_bindings": [{k: v for k, v in row.items() if k != "document"} for row in bound.values()],
        "unchanged_raw_answer_is_model_only_baseline": True,
        "semantic_scores_are_not_increased_by_program": True,
    }
    try:
        parsed, result["parse_mode"] = old.parse_final(raw_final)
        result.update(old.check_output(parsed, bound))
        result["status"] = "bounded_checks_complete"
    except (old.EvidenceError, ValueError, TypeError) as exc:
        result.update(status="insufficient", error=str(exc))
    require(final_path.read_bytes() == raw_final, "final_changed_during_check")
    result["original_final_unchanged"] = True
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", choices=["X", "Y"], required=True)
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    result = run(args.repeat, args.final, args.output, args.receipt, args.plan)
    print(json.dumps({"status": result["status"],
                      "documents_bound": sum(x["status"] == "source_bound" for x in result["document_bindings"]),
                      "local_statuses": [x["status"] for x in result.get("local_checks", [])]}))


if __name__ == "__main__":
    main()
