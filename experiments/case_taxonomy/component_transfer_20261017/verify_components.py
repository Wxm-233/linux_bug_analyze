"""Verify the small declared component freeze; never scan source candidates."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    manifest = json.loads((HERE / "component_versions.json").read_text(encoding="utf-8"))
    changed = []
    for record in manifest["files"]:
        path = ROOT / record["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            changed.append(record["path"])
    for relative, field in (("protocol_pre.json", "protocol_sha256"), ("method_scope.md", "method_scope_sha256")):
        if hashlib.sha256((HERE / relative).read_bytes()).hexdigest() != manifest[field]:
            changed.append(relative)
    try:
        parser = importlib.metadata.version("pycparser")
    except importlib.metadata.PackageNotFoundError:
        parser = None
    actual = {"python": sys.version.split()[0], "platform": sys.platform, "pycparser": parser}
    expected = manifest["source_analysis_runtime"]
    matched = actual == expected
    print(json.dumps({"files_checked": len(manifest["files"]), "changed_files": changed,
                      "runtime": actual, "source_analysis_runtime_matches": matched,
                      "status": "declared_components_match" if not changed and matched else "stop_frozen_run",
                      "complete_detector_verified": False}, ensure_ascii=False))
    return 0 if not changed and matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
