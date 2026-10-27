"""Run a frozen topology source-extraction grid without changing the selected code.

The selection JSON contains SHA-256 hashes for this runner, the protocol,
the extractor, and the evaluator. Errors remain errors rather than being
silently converted to contract verdicts.
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from contract_check_pilot_v1 import capability
from topology_contract_extract import from_git


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    case_dir = args.selection.resolve().parent
    expected = {
        "protocol_sha256": case_dir / "topology_v2_holdout_protocol_pre.md",
        "runner_sha256": Path(__file__).resolve(),
        "extractor_sha256": case_dir / "topology_contract_extract.py",
        "evaluator_sha256": case_dir / "contract_check_pilot_v1.py",
    }
    for key, path in expected.items():
        actual = digest(path)
        if selection[key] != actual:
            raise ValueError(f"frozen {key} mismatch: {path}")

    resolved_revisions = {}
    for candidate in selection["candidates"]:
        for revision in candidate["revision_pair"]:
            resolved_revisions[revision] = subprocess.check_output(
                ["git", "-C", str(args.linux_dir), "rev-parse", "--verify",
                 f"{revision}^{{commit}}"], text=True).strip()

    started = datetime.now(timezone.utc).isoformat()
    records = []
    for candidate in selection["candidates"]:
        for revision in candidate["revision_pair"]:
            for family in candidate["families"]:
                for profile in candidate["profiles"]:
                    row = {
                        "candidate": candidate["hash"],
                        "requested_revision": revision,
                        "resolved_revision": resolved_revisions[revision],
                        "family": family,
                        "profile": profile,
                    }
                    try:
                        evidence = from_git(
                            args.linux_dir, revision, profile["arch"],
                            profile["smp"], profile["sysfs"], family,
                            profile.get("sched_topology"))
                        status, reason = capability(evidence["records"][0])
                        row.update(status=status, reason=reason,
                                   evidence=evidence)
                    except Exception as exc:
                        row.update(status="runner_error",
                                   reason=f"{type(exc).__name__}: {exc}")
                    records.append(row)
    output = {
        "selection_sha256": digest(args.selection),
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "records": records,
    }
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    statuses = sorted({row["status"] for row in records})
    print(json.dumps({"records": len(records),
                      "statuses": {
                          status: sum(row["status"] == status for row in records)
                          for status in statuses
                      }}))


if __name__ == "__main__":
    main()
