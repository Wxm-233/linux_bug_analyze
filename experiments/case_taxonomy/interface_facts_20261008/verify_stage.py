"""Check saved development evidence and closeout hashes, without rerunning it."""
import argparse
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def safe(relative):
    path = (BASE / relative).resolve()
    path.relative_to(BASE.resolve())
    return path


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def check():
    result = read(HERE / "results.json")
    require(result["revision_observations"] == 8 and len(result["observations"]) == 8,
            "four development interfaces/two versions")
    require(result["new_confirmed_cases"] == 0 and not result["generalization_accuracy_established"] and
            not result["kernel_device_execution"] and result["model_calls"] == 0,
            "do not promote development to discovery/runtime")
    sources = {s["path"]: s for s in result["source_inventory"]}
    for s in sources.values():
        path = safe(s["path"])
        require(digest(path) == s["sha256"], "saved source SHA")
        raw = path.read_bytes()
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == s["blob_sha1"], "saved Git blob")
    quotes = 0
    for entry in walk(result):
        if {"saved_path", "source_path", "start_line", "end_line", "text", "blob_sha1"}.issubset(entry):
            s = sources.get(entry["saved_path"])
            require(s is not None and s["sha256"] == entry["sha256"] and
                    s["blob_sha1"] == entry["blob_sha1"] and s["revision"] == entry["revision"] and
                    s["source_path"] == entry["source_path"], "quote identity")
            lines = safe(entry["saved_path"]).read_text(encoding="utf-8").splitlines()
            a, b = entry["start_line"], entry["end_line"]
            require(1 <= a <= b <= len(lines) and "\n".join(lines[a - 1:b]) == entry["text"], "literal quote")
            quotes += 1
        if entry.get("kind") == "existing_human_review":
            require(digest(safe(entry["path"])) == entry["sha256"], "human review unchanged")
            require(entry["semantic_status"] == "reviewed_claims_not_machine_certified", "review boundary")
    for path, expected in result["execution_code_sha256"].items():
        require(digest(safe(path)) == expected, "executed code unchanged")
    receipt = read(HERE / "execution_receipt.json")
    require(receipt["code_unchanged"] and len(receipt["commands"]) == 2 and
            [c["name"] for c in receipt["commands"]] == ["tests", "development"] and
            all(c["returncode"] == 0 for c in receipt["commands"]), "captured successful commands")
    for name, expected in receipt["code_sha256"].items():
        require(digest(HERE / name) == expected, "tested execution source")
    test_output = (HERE / "tests_stderr.txt").read_text(encoding="utf-8")
    require(re.search(r"Ran 47 tests\b", test_output) and test_output.rstrip().endswith("OK"), "47 boundary tests")
    syntax_audit = read(HERE / "audit_source_shape/after_case_guard_execution.json")
    current_extractor = digest(HERE / "interface_fact_extractor.py")
    require(syntax_audit["extractor_unchanged_during_run"] and
            syntax_audit["initial_current_extractor_sha256"] == current_extractor and
            syntax_audit["post_run_current_extractor_sha256"] == current_extractor and
            len(syntax_audit["runs"]) == 3 and all(r["exit_code"] == 0 for r in syntax_audit["runs"]),
            "independent final syntax audit bound to extractor")
    by_case = {(o["case"], o["label"]): o for o in result["observations"]}
    require(len(by_case) == 8, "unique revisions")
    for label in ("parent", "fixed"):
        o = by_case["ocfs2", label]
        require(o["primary"][0]["status"] == ("candidate" if label == "parent" else "normal"), "ocfs2 reviewed mask")
        require(all(v[0]["status"] == "normal" for v in o["controls"].values()), "local zero controls")
        require(o["mask_literals"]["value"] == 0xc60, "literal mask")
        o = by_case["pwm", label]
        require(o["visible_value_domain"]["values"] == [0] and
                o["visible_value_domain"]["call_count"] == 1 and
                o["current_visible_value_byte_difference"] is False, "visible zero caller")
        require(o["primary"]["status"] == ("candidate" if label == "parent" else "normal"), "PWM local type")
        require(o["control"]["status"] == "normal", "PWM setter control")
        o = by_case["smb", label]
        require(o["primary"]["status"] == "normal" and
                o["primary"]["format_carriers"][0]["value"] == "UTF16_LITTLE_ENDIAN" and
                o["primary"]["whole_encoder_certified"] is False, "API selector is a local fact")
        require(sum(len(c) for c in o["controls"].values()) == 4 and
                all(c["status"] == "not_value_read" for values in o["controls"].values() for c in values), "four fixed scalar sizeof references")
        o = by_case["ath12k", label]
        require(o["primary"]["direction"] == "read" and
                o["primary"]["status"] == ("insufficient" if label == "parent" else "normal"), "ath12k read scope")
        require(o["primary"]["hardware_mode"]["actual_selected_ring_flags"] == "unknown" and
                not o["primary"]["runtime_fault_proven"], "hardware mode unknown")
    return dict(development_interfaces=4, revision_observations=8,
                verified_source_files=len(sources), literal_quotes=quotes,
                boundary_tests=47, independent_boundary_probes=32,
                new_confirmed_cases=0, model_calls=0, runtime_experiment=False,
                semantic_truth_certified_by_hash_check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    summary = check()
    lock = HERE / "closeout_manifest.json"
    if args.freeze:
        require(not lock.exists(), "refuse overwrite of final lock")
        require((HERE / "audit_result/audit.json").exists() and
                (HERE / "audit_result/review_final.md").exists(), "final result review missing")
        audit = read(HERE / "audit_result/audit.json")
        require(audit["result_sha256"] == digest(HERE / "results.json") and
                audit["extractor_sha256"] == digest(HERE / "interface_fact_extractor.py") and
                not audit["blockers_reported"], "result review bound to final output")
        files = [p for p in HERE.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p != lock]
        dependencies = [BASE / s["path"] for s in read(HERE / "results.json")["source_inventory"]]
        dependencies.extend(safe(e["path"]) for e in walk(read(HERE / "results.json")) if e.get("kind") == "existing_human_review")
        dependencies.append(BASE / "endian_consumer_single_revision.py")
        dependencies.extend(BASE / p for p in (
            "cross_subsystem_facts_20261003/ocfs2/source_manifest.json",
            "cross_subsystem_facts_20261003/pwm/source_manifest.json",
            "bounded_interface_holdout_20261003/source_manifest.json",
            "bounded_interface_holdout_20261003/consumer/manual_review/source_manifest_extra.json",
            "bounded_interface_holdout_20261003/producer/manual_review/source_manifest_extra.json"))
        payload = dict(scope="post-development closeout, not pre-unseen freeze", summary=summary,
            files=[dict(path=p.relative_to(BASE).as_posix(), sha256=digest(p))
                   for p in sorted(set(files + dependencies))])
        lock.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if lock.exists():
        for item in read(lock)["files"]:
            require(digest(safe(item["path"])) == item["sha256"], "closed file changed")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
