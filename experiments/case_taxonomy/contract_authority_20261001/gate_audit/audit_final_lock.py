"""Read-only checks of the final development gate run and 17-test lock."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARENT = "cef456cd354ef485f12d57000c455e83e416a2b6"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    final = ROOT / "development_final_lock"
    results = load(final / "results.json")
    tests = load(ROOT / "root_test_final_lock.json")
    sources = load(final / "source_files.json")
    prior = ROOT.parent / "contract_assertions_20261001" / "final_run_01" / "parent_plan.json"
    assert results["gate_sha256"] == sha(ROOT / "authority_gate.py")
    assert results["gate_unchanged_during_run"] is True
    assert results["runner_sha256"] == sha(ROOT / "run_gate_development.py")
    assert results["input_plan_sha256"] == sha(prior)
    assert tests["returncode"] == 0
    assert "Ran 17 tests" in tests["stderr"] and "OK" in tests["stderr"]
    assert tests["tested_files"]["authority_gate.py"] == results["gate_sha256"]
    assert tests["tested_files"]["authority_gate_test.py"] == sha(ROOT / "authority_gate_test.py")
    assert tests["code_unchanged_during_test"] is True

    original = load(ROOT / "source_authority" / "evidence.json")
    originals = {source["path"]: source for source in original["sources"]}
    source_checks = {}
    for path, item in sources.items():
        raw = item["text"].encode("utf-8")
        computed_sha = hashlib.sha256(raw).hexdigest()
        computed_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        assert item["revision"] == PARENT
        assert item["sha256"] == computed_sha and item["git_blob"] == computed_blob
        if path in originals:
            assert item["text"] == originals[path]["full_text"]
            assert item["sha256"] == originals[path]["full_file_sha256"]
        source_checks[path] = {"sha256": computed_sha, "git_blob": computed_blob,
                               "matches_independent_raw_export": path in originals}
    assert source_checks["include/linux/skbuff.h"]["git_blob"] == "0a58402a166e3835e84b0f2662aed6771878eae7"

    expected = {
        "local_source_review": ("source_contract_ready", "matched"),
        "historical_external_pending": ("conditional", "matched"),
        "missing_source_reference": ("insufficient", "insufficient"),
        "reported_conflict": ("conflict", "matched"),
        "no_review_card": ("insufficient", "not_checked"),
    }
    assert set(results["outputs"]) == set(expected)
    output_checks = {}
    for key, output in results["outputs"].items():
        assert (output["status"], output["reference_integrity"]["status"]) == expected[key]
        for claim in ("machine_contract_proven", "runtime_reachability_proven", "full_kernel_proven", "external_protocol_proven"):
            assert output[claim] is False
        output_checks[key] = {"status": output["status"],
                              "reference_integrity": output["reference_integrity"]["status"],
                              "proof_flags": "all_false"}

    card = load(final / "local_source_card.json")
    assert card["review"]["reviewer_kind"] == "assistant"
    assert card["review"]["scope"] == "source_contract"
    report = {
        "scope": "read-only final development-lock artifact audit; no compile or new detector label",
        "gate_sha256": results["gate_sha256"],
        "runner_sha256": results["runner_sha256"],
        "tests": {"count": 17, "returncode": 0, "code_unchanged": True},
        "output_checks": output_checks,
        "source_checks": source_checks,
        "independently_observed_parent_git_tree": {
            "command": f"git -C /root/repos/linux ls-tree {PARENT} include/linux/skbuff.h",
            "blob": "0a58402a166e3835e84b0f2662aed6771878eae7",
        },
        "limits": [
            "source_contract_ready is attributed assistant review with exact references, not machine semantic proof",
            "historical external Bluetooth specification applicability remains unknown",
            "runtime/kernel/controller proof flags remain false",
        ],
    }
    target = HERE / "final_audit.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print("FINAL_GATE_LOCK_AUDIT_OK")


if __name__ == "__main__":
    main()
