"""Development replay of a previously read case; never a held-out test."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULES = HERE.parent.parent
sys.path.insert(0, str(MODULES))
import structured_hci_single_revision as detector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, default=Path("/root/repos/linux"))
    args = parser.parse_args()
    cases = [("parent", "cef456cd354ef485f12d57000c455e83e416a2b6"),
             ("fix", "727ea61a5028f8ac96f75ab34cb1b56e63fd9227")]
    outputs = []
    for name, revision in cases:
        report = detector.analyze_revision(args.linux_dir, revision, "net/bluetooth/hci_core.c")
        path = HERE / f"hci_core_{name}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        targets = [item for item in report["findings"] if item["struct"] == "hci_cp_le_write_def_data_len"]
        outputs.append({"name": name, "revision": revision, "report": path.name,
            "report_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "counts": report["counts"],
            "known_target_fields": [{"field": item["field"], "status": item["status"],
                "assignment_line": item["assignment"]["line"],
                "target_type": item["target_declaration"]["type"] if item["target_declaration"] else None,
                "source_type": item["source_member"]["declaration"]["type"] if item["source_member"] else None} for item in targets]})
    result = {"scope": "known-case development replay, not independent evidence; no hardware/configuration claim",
        "module_sha256": hashlib.sha256(Path(detector.__file__).read_bytes()).hexdigest(),
        "test_sha256": hashlib.sha256((MODULES / "structured_hci_single_revision_test.py").read_bytes()).hexdigest(),
        "dependencies": report["dependencies"], "outputs": outputs}
    (HERE / "known_replay_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": [item["counts"] for item in outputs], "fields": [item["known_target_fields"] for item in outputs]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
