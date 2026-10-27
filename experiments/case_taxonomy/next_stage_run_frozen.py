"""Replay the preregistered topology scope grid without editing the extractor."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from contract_check_pilot_v1 import capability
from topology_contract_extract import from_git


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    root = args.selection.resolve().parents[2]
    case_dir = args.selection.resolve().parent
    expected = {
        "protocol_sha256": case_dir / "next_stage_protocol_pre.md",
        "extractor_sha256": case_dir / "topology_contract_extract.py",
        "evaluator_sha256": case_dir / "contract_check_pilot_v1.py",
        "fixed_500_manifest_sha256": root / "analysis_out/stratified-20260921/manifest.json",
    }
    for field, path in expected.items():
        actual = sha256(path)
        if selection[field] != actual:
            raise ValueError(f"frozen {field} mismatch: {path}")

    grid = selection["topology_metadata_pool"]["frozen_run"]
    started = datetime.now(timezone.utc).isoformat()
    records = []
    for revision in grid["revision_pair"]:
        for family in grid["families"]:
            for profile in grid["profiles"]:
                evidence = from_git(args.linux_dir, revision, profile["arch"],
                                    profile["smp"], profile["sysfs"], family)
                row = evidence["records"][0]
                status, reason = capability(row)
                records.append({"requested_revision": revision,
                                "family": family, "profile": profile,
                                "status": status, "reason": reason,
                                "evidence": evidence})
    output = {"selection_sha256": sha256(args.selection),
              "started_utc": started,
              "finished_utc": datetime.now(timezone.utc).isoformat(),
              "records": records}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"records": len(records),
                      "statuses": {status: sum(row["status"] == status for row in records)
                                   for status in ("hit", "normal", "not_applicable", "insufficient")}}))


if __name__ == "__main__":
    main()
