"""Replay frozen bcachefs representation holdouts and preserve raw outcomes."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from bcachefs_auto_layout_extract import analyze_texts, header_at


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
        "protocol_sha256": case_dir / "bcachefs_auto_holdout_protocol_pre.md",
        "extractor_sha256": case_dir / "bcachefs_auto_layout_extract.py",
        "runner_sha256": Path(__file__).resolve(),
    }
    for key, path in expected.items():
        actual = digest(path)
        if selection[key] != actual:
            raise ValueError(f"frozen {key} mismatch: {path}")

    profiles = {
        "x86_64_little": ("gcc", []),
        "s390x_big": ("s390x-linux-gnu-gcc",
                      ["qemu-s390x", "-L", "/usr/s390x-linux-gnu"]),
    }
    started = datetime.now(timezone.utc).isoformat()
    records = []
    for candidate in selection["candidates"]:
        revision = candidate["hash"]
        path = selection["header"]
        try:
            old_id, old = header_at(args.linux_dir, revision + "^", path)
            fixed_id, fixed = header_at(args.linux_dir, revision, path)
            result = analyze_texts(
                old, fixed, path=path, old_revision=old_id,
                fixed_revision=fixed_id, profiles=profiles)
            record = {"candidate": revision, "status": "analyzed",
                      "result": result}
        except Exception as exc:
            record = {"candidate": revision, "status": "runner_error",
                      "reason": f"{type(exc).__name__}: {exc}"}
        records.append(record)
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
    print(json.dumps({
        "revisions": len(records),
        "analyzed": sum(row["status"] == "analyzed" for row in records),
        "runner_error": sum(row["status"] == "runner_error" for row in records),
        "candidate_sites": sum(len(row["result"]["candidates"])
                               for row in records if row["status"] == "analyzed"),
    }))


if __name__ == "__main__":
    main()
