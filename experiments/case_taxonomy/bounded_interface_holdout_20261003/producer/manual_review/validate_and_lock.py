"""Validate saved manual evidence and record a final leaf inventory."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


review = json.loads((HERE / "review.json").read_text(encoding="utf-8"))
extra = json.loads((HERE / "source_manifest_extra.json").read_text(encoding="utf-8"))
assert len(extra) == 8
assert all(sum(item["label"] == label for item in extra) == 4 for label in ("parent", "fixed"))
for item in extra + review["quotes"]:
    raw = (STAGE / item["saved_path"]).read_bytes()
    assert sha(raw) == item["sha256"]
    assert hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() == item["blob_sha1"]
    if "text" in item:
        assert "\n".join(raw.decode("utf-8").splitlines()[item["start_line"]-1:item["end_line"]]) == item["text"]
commands = json.loads((HERE / "commands_extra.json").read_text(encoding="utf-8"))
assert len(commands) == 16
for item in commands:
    assert item["returncode"] == 0
    for stream in ("stdout", "stderr"):
        assert sha((STAGE / item[stream]).read_bytes()) == item[stream + "_sha256"]
for item in review["raw_outputs"].values():
    assert sha((STAGE / item["path"]).read_bytes()) == item["sha256"]
assert sha((STAGE / review["patch"]["path"]).read_bytes()) == review["patch"]["sha256"]
assert review["new_confirmed_defect_count"] == 0
files = [{"path": path.relative_to(STAGE).as_posix(), "bytes": path.stat().st_size,
          "sha256": sha(path.read_bytes())} for path in sorted(HERE.rglob("*"))
         if path.is_file() and path.name != "locked_manifest.json"]
manifest = {"locked_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "pass", "extra_source_records": 8, "quote_records": len(review["quotes"]),
            "source_blob_sha1_and_sha256_verified": True, "source_line_quotes_verified": True,
            "command_streams_and_original_raw_patch_hash_verified": True,
            "scope": "saved-artifact integrity only; no runtime or external-contract test",
            "self_excluded": "locked_manifest.json", "files": files}
(HERE / "locked_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "pass", "files": len(files), "quotes": len(review["quotes"]),
                  "review_md_sha256": sha((HERE / "review.md").read_bytes()),
                  "review_json_sha256": sha((HERE / "review.json").read_bytes()),
                  "source_manifest_extra_sha256": sha((HERE / "source_manifest_extra.json").read_bytes()),
                  "locked_manifest_sha256": sha((HERE / "locked_manifest.json").read_bytes())}))
