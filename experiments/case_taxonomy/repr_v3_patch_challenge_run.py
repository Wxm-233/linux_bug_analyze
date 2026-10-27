"""Run the frozen v3 source checker on preselected parent revisions only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from representation_producer_v3 import analyze_revision  # noqa: E402


EXPECTED_CHECKER_SHA256 = "ef9e292fe414ab597931d161bb10fdf35a8fd22b1cde6df3a91b05417ce91a9c"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    checker_path = HERE / "representation_producer_v3.py"
    checker_sha = digest(checker_path.read_bytes())
    if checker_sha != EXPECTED_CHECKER_SHA256:
        raise RuntimeError(f"frozen checker changed: {checker_sha}")
    selection_bytes = args.selection.read_bytes()
    selection = json.loads(selection_bytes)
    targets = selection["targets"]
    if len(targets) > 3:
        raise RuntimeError("selection exceeds the predeclared cap")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for item in targets:
        commit = item["fix_commit"]
        parent = item["old_revision"]
        path = item["source_path"]
        try:
            report = analyze_revision(args.repo, parent, path)
            report["challenge_role"] = "patch-informed parent revision"
            runner_status = "ok"
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            report = {
                "revision": parent,
                "source_file": path,
                "runner_error": f"{type(exc).__name__}: {exc}",
            }
            runner_status = "runner_error"
        raw = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        output = args.out_dir / f"repr_v3_patch_challenge_{commit[:8]}_raw.json"
        output.write_bytes(raw)
        records.append({
            "fix_commit": commit,
            "old_revision": parent,
            "source_path": path,
            "raw_file": output.name,
            "bytes": len(raw),
            "sha256": digest(raw),
            "runner_status": runner_status,
        })
    manifest = {
        "stage": "all patch-selected parent-source outputs saved before manual result or patch review",
        "saved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "selection_sha256": digest(selection_bytes),
        "checker_sha256": checker_sha,
        "records": records,
        "interpretation_limit": "Patch-informed challenge only; do not call this blind discovery or population accuracy.",
    }
    path = args.out_dir / "repr_v3_patch_challenge_raw_manifest_pre_review.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


if __name__ == "__main__":
    main()
